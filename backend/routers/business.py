from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from ..database import SessionLocals
from ..security import get_current_user
from .. import models

router = APIRouter(prefix="/business", tags=["核心业务 (医生开药)"])

class PrescriptionRequest(BaseModel):
    medicine_id: int
    quantity: int

class StockItem(BaseModel):
    medicine_id: int
    quantity: int

# 【核心修复】定义数据库到仓库ID的映射关系
# mysql -> 仓库1, pg -> 仓库2, mssql -> 仓库3
DB_WAREHOUSE_MAP = {
    "mysql": 1,
    "pg": 2,
    "mssql": 3
}

@router.post("/prescribe")
def prescribe_medicine(
    req: PrescriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    db_name = current_user.get("db_name")
    
    if not db_name:
        raise HTTPException(status_code=400, detail="User database unknown")

    print(f"💊 用户 {current_user['username']} (ID: {user_id}) 正在开药...")

    db = SessionLocals[db_name]()
    try:
        if db_name == "mssql":
            sql = text(f"EXEC sp_prescribe_medicine @p_user_id={user_id}, @p_medicine_id={req.medicine_id}, @p_quantity={req.quantity}")
        else:
            sql = text(f"CALL sp_prescribe_medicine({user_id}, {req.medicine_id}, {req.quantity})")
        
        db.execute(sql)
        db.commit()
        return {"status": "success", "message": "开药成功！库存已扣减。"}

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "权限不足" in error_msg:
            clean_msg = "权限不足：您无法开具此类药品！"
        elif "库存不足" in error_msg:
            clean_msg = "操作失败：当前药房库存不足！"
        else:
            clean_msg = f"系统错误: {error_msg}"
        raise HTTPException(status_code=400, detail=clean_msg)
    finally:
        db.close()

@router.get("/stock/{db_name}", response_model=list[StockItem])
def get_warehouse_stock(db_name: str):
    """
    获取指定数据库中，属于该院区的所有库存。
    【修复】：增加过滤，只返回该数据库对应仓库的数据，防止数据覆盖。
    """
    db = SessionLocals[db_name]()
    try:
        # 获取该数据库对应的 本地仓库ID
        target_warehouse_id = DB_WAREHOUSE_MAP.get(db_name)
        
        query = db.query(models.Inventory)
        
        # 如果能匹配到仓库ID，就只查这个仓库的库存
        if target_warehouse_id:
            query = query.filter(models.Inventory.warehouse_id == target_warehouse_id)
        
        # (如果是总院 mssql，根据业务需求，可能想看 warehouse 3，或者看全部)
        # 这里我们设定：查 mssql 时，只返回 总院仓库(3) 的库存。
        # 如果想看所有，那是报表页面的事，不是开药页面的事。
        
        items = query.all()
        return items
    finally:
        db.close()