from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
from ..database import SessionLocals
from ..security import get_current_user
from .. import models

router = APIRouter(prefix="/business", tags=["核心业务"])

# --- Schemas ---
class PrescriptionItemReq(BaseModel):
    medicine_id: int
    quantity: int

class PrescriptionCreate(BaseModel):
    patient_name: str
    items: List[PrescriptionItemReq]

class AllocationReq(BaseModel):
    source_branch_id: int  # 【修正】支持任意源仓库
    target_branch_id: int  # 支持任意目标仓库
    medicine_id: int
    quantity: int

class StockItem(BaseModel):
    medicine_id: int
    quantity: int

class AuditLogOut(BaseModel):
    create_time: datetime
    operation_type: str
    description: Optional[str] = None
    change_amount: int
    medicine_name: Optional[str] = None
    class Config:
        from_attributes = True

class PrescriptionOut(BaseModel):
    id: int
    prescription_no: str
    patient_name: str
    total_amount: float
    create_time: datetime
    warehouse_id: int
    doctor_id: int
    class Config:
        from_attributes = True

class PrescriptionItemOut(BaseModel):
    medicine_name: str
    quantity: int
    price_snapshot: float
    line_total: float

DB_WAREHOUSE_MAP = {"mysql": 1, "pg": 2, "mssql": 3}

# --- 1. 创建处方 ---
@router.post("/prescription/create")
def create_prescription(req: PrescriptionCreate, current_user: dict = Depends(get_current_user)):
    db_name = current_user['db_name']
    db = SessionLocals[db_name]()
    try:
        pres_no = f"RX-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        new_pres = models.Prescription(
            prescription_no=pres_no,
            patient_name=req.patient_name,
            doctor_id=current_user['id'],
            warehouse_id=current_user['branch_id'],
            total_amount=0.0
        )
        db.add(new_pres)
        db.flush()

        total_price = 0.0
        for item in req.items:
            # 1. 扣库存 (存储过程)
            if db_name == "mssql":
                sql = text(f"EXEC sp_process_prescription_item @p_user_id={current_user['id']}, @p_medicine_id={item.medicine_id}, @p_quantity={item.quantity}")
            else:
                sql = text(f"CALL sp_process_prescription_item({current_user['id']}, {item.medicine_id}, {item.quantity})")
            db.execute(sql)
            
            # 2. 记明细
            med = db.query(models.Medicine).filter(models.Medicine.id == item.medicine_id).first()
            line_total = med.price * item.quantity
            total_price += line_total
            
            new_item = models.PrescriptionItem(
                prescription_id=new_pres.id,
                medicine_id=item.medicine_id,
                quantity=item.quantity,
                price_snapshot=med.price
            )
            db.add(new_item)
            
            # 3. 记日志
            audit = models.AuditLog(
                medicine_id=item.medicine_id,
                warehouse_id=current_user['branch_id'],
                change_amount=-item.quantity,
                operation_type="PRESCRIPTION",
                operator_id=current_user['id'],
                description=f"处方: {pres_no}"
            )
            db.add(audit)

        new_pres.total_amount = total_price
        db.commit()
        return {"status": "success", "message": "开方成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))
    finally:
        db.close()

# --- 2. 物资调拨 (修正版：本地操作触发同步冲突) ---
@router.post("/allocation/create")
def create_allocation(req: AllocationReq, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin':
        raise HTTPException(403, "权限不足")
    
    if req.source_branch_id == req.target_branch_id:
        raise HTTPException(400, "源仓库和目标仓库不能相同")

    # 逻辑：只修改当前数据库 (MSSQL) 里的记录
    db = SessionLocals[current_user['db_name']]() # 通常是 mssql
    try:
        # 1. 扣减源仓库 (本地副本)
        source_inv = db.query(models.Inventory).filter(
            models.Inventory.warehouse_id == req.source_branch_id,
            models.Inventory.medicine_id == req.medicine_id
        ).with_for_update().first()
        
        if not source_inv or source_inv.quantity < req.quantity:
            raise HTTPException(400, "源仓库库存不足")
            
        source_inv.quantity -= req.quantity
        source_inv.last_updated = datetime.now() # 更新时间戳 -> 触发后续冲突报警
        
        # 2. 增加目标仓库 (本地副本)
        target_inv = db.query(models.Inventory).filter(
            models.Inventory.warehouse_id == req.target_branch_id,
            models.Inventory.medicine_id == req.medicine_id
        ).first()
        
        if target_inv:
            target_inv.quantity += req.quantity
            target_inv.last_updated = datetime.now() # 更新时间戳 -> 触发后续冲突报警
        
        # 3. 记日志
        audit = models.AuditLog(
            medicine_id=req.medicine_id,
            warehouse_id=req.source_branch_id,
            change_amount=-req.quantity,
            operation_type="ALLOCATE",
            operator_id=current_user['id'],
            description=f"从[{req.source_branch_id}]调至[{req.target_branch_id}]"
        )
        db.add(audit)
        
        db.commit()
        return {"status": "success", "message": "调拨指令已在总院执行，等待冲突检测..."}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db.close()

# --- 3. 查询库存 ---
@router.get("/stock/{db_name}", response_model=List[StockItem])
def get_warehouse_stock(db_name: str):
    db = SessionLocals[db_name]()
    try:
        target_warehouse_id = DB_WAREHOUSE_MAP.get(db_name)
        query = db.query(models.Inventory)
        if target_warehouse_id:
            query = query.filter(models.Inventory.warehouse_id == target_warehouse_id)
        return query.all()
    finally:
        db.close()

# --- 4. 个人记录 (修复药名) ---
@router.get("/my-records", response_model=List[AuditLogOut])
def get_my_records(current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        # 使用 outerjoin 确保即使 medicine_id 偶尔为空也不会丢数据
        # 并且 select 明确指定 medicine.name
        results = db.query(
            models.AuditLog.create_time,
            models.AuditLog.operation_type,
            models.AuditLog.change_amount,
            models.AuditLog.description,
            models.Medicine.name.label("medicine_name")
        ).outerjoin(models.Medicine, models.AuditLog.medicine_id == models.Medicine.id)\
         .filter(models.AuditLog.operator_id == current_user['id'])\
         .order_by(models.AuditLog.create_time.desc()).all()
        return results
    finally:
        db.close()

# --- 5. 处方列表 ---
@router.get("/prescriptions", response_model=List[PrescriptionOut])
def get_prescriptions(current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        query = db.query(models.Prescription)
        if current_user['role'] != 'super_admin':
            query = query.filter(models.Prescription.warehouse_id == current_user['branch_id'])
        return query.order_by(models.Prescription.create_time.desc()).all()
    finally:
        db.close()

# --- 6. 处方详情 (新增) ---
@router.get("/prescription/{pres_id}/items", response_model=List[PrescriptionItemOut])
def get_prescription_items(pres_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        items = db.query(
            models.Medicine.name.label("medicine_name"),
            models.PrescriptionItem.quantity,
            models.PrescriptionItem.price_snapshot,
            (models.PrescriptionItem.quantity * models.PrescriptionItem.price_snapshot).label("line_total")
        ).join(models.Medicine, models.PrescriptionItem.medicine_id == models.Medicine.id)\
         .filter(models.PrescriptionItem.prescription_id == pres_id)\
         .all()
        return items
    finally:
        db.close()