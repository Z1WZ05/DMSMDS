from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas

# 创建路由实例
router = APIRouter(
    prefix="/medicines",
    tags=["药品管理 (基础数据)"]
)

# 1. 查询药品列表
@router.get("/{db_name}", response_model=list[schemas.Medicine])
def read_medicines(db_name: str, db: Session = Depends(get_db)):
    """
    获取指定数据库 (mysql, pg, mssql) 中的所有药品。
    用于验证数据同步是否成功 (比如改了 MySQL，看 PG 变没变)。
    """
    medicines = db.query(models.Medicine).all()
    return medicines

# 2. 查询单个药品
@router.get("/{db_name}/{medicine_id}", response_model=schemas.Medicine)
def read_medicine(db_name: str, medicine_id: int, db: Session = Depends(get_db)):
    medicine = db.query(models.Medicine).filter(models.Medicine.id == medicine_id).first()
    if medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return medicine

# 3. 修改药品信息 (关键接口：用于制造同步触发源 或 制造冲突)
@router.put("/{db_name}/{medicine_id}", response_model=schemas.Medicine)
def update_medicine(
    db_name: str, 
    medicine_id: int, 
    medicine_update: schemas.MedicineCreate, # 使用 schemas 接收前端数据
    db: Session = Depends(get_db)
):
    """
    修改指定数据库中的药品信息。
    场景：
    1. 正常修改：改 MySQL -> 触发同步 -> 其他库自动更新。
    2. 制造冲突：暂停同步 -> 改 MySQL 价格为 10 -> 改 PG 价格为 20 -> 开启同步 -> 爆炸💥。
    """
    # 查找
    db_medicine = db.query(models.Medicine).filter(models.Medicine.id == medicine_id).first()
    if not db_medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # 更新字段
    db_medicine.name = medicine_update.name
    db_medicine.price = medicine_update.price
    if medicine_update.category:
        db_medicine.category = medicine_update.category
    if medicine_update.danger_level:
        db_medicine.danger_level = medicine_update.danger_level
    
    # 提交事务
    db.commit()
    db.refresh(db_medicine)
    return db_medicine

# ... (前面的代码保持不变)

# 【新增】模拟总院管理员修改库存 (制造冲突专用接口)
@router.post("/simulate-central-update")
def simulate_central_update(
    warehouse_id: int,
    medicine_id: int,
    new_quantity: int,
    db: Session = Depends(get_db) # 默认依赖注入可能需要调整，这里建议直接在函数里获取 mssql session
):
    """
    【实验专用】模拟总院管理员手动修改库存，制造时间戳领先于分院的情况，从而触发冲突。
    """
    # 这里的 db 依赖如果默认不是 mssql，需要手动获取 mssql 的 session
    # 为了演示简单，我们假设 main.py 里 get_db 默认行为或这里手动通过 database.SessionLocals 获取
    from ..database import SessionLocals
    mssql_db = SessionLocals["mssql"]
    
    try:
        inventory = mssql_db.query(models.Inventory).filter(
            models.Inventory.warehouse_id == warehouse_id,
            models.Inventory.medicine_id == medicine_id
        ).first()
        
        if not inventory:
            raise HTTPException(status_code=404, detail="Inventory not found in Central DB")
        
        # 修改数量，更新时间戳
        inventory.quantity = new_quantity
        # SQLAlchemy 会自动更新 last_updated，或者手动更新：
        inventory.last_updated = func.now()
        
        mssql_db.commit()
        return {"message": "总院库存已修改，等待同步引擎触发冲突报警...", "new_quantity": inventory.quantity}
    except Exception as e:
        mssql_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        mssql_db.close()