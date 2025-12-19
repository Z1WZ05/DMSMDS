from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List
from datetime import datetime
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

class AuditLogOut(BaseModel):
    create_time: datetime
    operation_type: str
    medicine_name: str
    change_amount: int
    class Config:
        from_attributes = True

# 数据库 -> 仓库ID 映射
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
        # 调用存储过程
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

@router.get("/stock/{db_name}", response_model=List[StockItem])
def get_warehouse_stock(db_name: str):
    """
    获取指定数据库中，属于该院区的所有库存
    """
    db = SessionLocals[db_name]()
    try:
        # 只返回该数据库对应仓库的数据
        target_warehouse_id = DB_WAREHOUSE_MAP.get(db_name)
        query = db.query(models.Inventory)
        
        if target_warehouse_id:
            query = query.filter(models.Inventory.warehouse_id == target_warehouse_id)
        
        return query.all()
    finally:
        db.close()

@router.get("/my-records", response_model=List[AuditLogOut])
def get_my_records(current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        results = db.query(
            models.AuditLog.create_time,
            models.AuditLog.operation_type,
            models.AuditLog.change_amount,
            models.Medicine.name.label("medicine_name")
        ).join(models.Medicine, models.AuditLog.medicine_id == models.Medicine.id)\
         .filter(models.AuditLog.operator_id == current_user['id'])\
         .order_by(models.AuditLog.create_time.desc()).all()
        return results
    finally:
        db.close()