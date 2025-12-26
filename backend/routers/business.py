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
from ..sync_engine import sync_logic 
from ..config import settings
import time

router = APIRouter(prefix="/business", tags=["核心业务"])

# --- 数据校验模型 ---
class PrescriptionItemReq(BaseModel):
    medicine_id: int
    quantity: int

class PrescriptionCreate(BaseModel):
    patient_name: str
    items: List[PrescriptionItemReq]

class AllocationReq(BaseModel):
    source_branch_id: int
    target_branch_id: int
    medicine_id: int
    quantity: int

class InboundReq(BaseModel):
    warehouse_id: int
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
    id: str
    prescription_no: str
    patient_name: str
    total_amount: float
    create_time: datetime
    warehouse_id: int
    doctor_id: int
    doctor_name: str
    class Config:
        from_attributes = True

class PrescriptionItemOut(BaseModel):
    medicine_name: str
    quantity: int
    price_snapshot: float
    line_total: float

class AdminActionOut(BaseModel):
    id: int
    action_type: str
    details: str
    create_time: datetime
    class Config:
        from_attributes = True

DB_BRANCH_NAMES = {1: "第一分院(MySQL)", 2: "第二分院(PG)", 3: "集团总院(MSSQL)"}

# --- 1. 创建处方 ---
@router.post("/prescription/create")
def create_prescription(req: PrescriptionCreate, current_user: dict = Depends(get_current_user)):
    db_name = current_user['db_name']
    db = SessionLocals[db_name]()
    try:
        now_time = datetime.now()
        pres_no = f"RX-{now_time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        pres_uuid = str(uuid.uuid4())
        new_pres = models.Prescription(id=pres_uuid, prescription_no=pres_no, patient_name=req.patient_name,
                                      doctor_id=current_user['id'], warehouse_id=current_user['branch_id'],
                                      total_amount=0.0, create_time=now_time, last_updated=now_time)
        db.add(new_pres)
        total_price = 0.0
        for item in req.items:
            if db_name == "mssql":
                sql = text(f"EXEC sp_process_prescription_item @p_user_id={current_user['id']}, @p_medicine_id={item.medicine_id}, @p_quantity={item.quantity}")
            else:
                sql = text(f"CALL sp_process_prescription_item({current_user['id']}, {item.medicine_id}, {item.quantity})")
            db.execute(sql)
            med = db.query(models.Medicine).filter(models.Medicine.id == item.medicine_id).first()
            total_price += med.price * item.quantity
            db.add(models.PrescriptionItem(id=str(uuid.uuid4()), prescription_id=pres_uuid, medicine_id=item.medicine_id,
                                          quantity=item.quantity, price_snapshot=med.price, last_updated=now_time))
            db.add(models.AuditLog(medicine_id=item.medicine_id, warehouse_id=current_user['branch_id'],
                                  change_amount=-item.quantity, operation_type="PRESCRIPTION",
                                  operator_id=current_user['id'], description=f"处方: {pres_no}", create_time=now_time))
        new_pres.total_amount = total_price
        db.commit()
        if settings.REAL_TIME_SYNC:
            try: 
                time.sleep(1)
                sync_logic()
            except: pass
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))
    finally: db.close()

# --- 2. 物资调配 (增加健壮性检查) ---
@router.post("/allocation/create")
def create_allocation(req: AllocationReq, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin': raise HTTPException(403)
    db = SessionLocals[current_user['db_name']]()
    try:
        now_time = datetime.now()
        s_inv = db.query(models.Inventory).filter(models.Inventory.warehouse_id == req.source_branch_id, models.Inventory.medicine_id == req.medicine_id).first()
        t_inv = db.query(models.Inventory).filter(models.Inventory.warehouse_id == req.target_branch_id, models.Inventory.medicine_id == req.medicine_id).first()
        med = db.query(models.Medicine).filter(models.Medicine.id == req.medicine_id).first()
        
        if not s_inv or s_inv.quantity < req.quantity: raise HTTPException(400, "源仓库库存不足或记录缺失")
        if not t_inv: raise HTTPException(400, "目标仓库中该药品记录缺失，请先办理入库")
        
        s_inv.quantity -= req.quantity
        s_inv.last_updated = now_time
        t_inv.quantity += req.quantity
        t_inv.last_updated = now_time
        
        detail = f"【调配】从 {DB_BRANCH_NAMES.get(req.source_branch_id)} 调拨 {med.name} x{req.quantity} 至 {DB_BRANCH_NAMES.get(req.target_branch_id)}"
        db.add(models.AdminAction(operator_id=current_user['id'], action_type="ALLOCATE", details=detail, create_time=now_time))
        db.commit()
        if settings.REAL_TIME_SYNC:
            try: 
                time.sleep(1)
                sync_logic()
            except: pass
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=str(e))
    finally: db.close()

# --- 3. 物资入库 (增加健壮性检查) ---
@router.post("/inbound/create")
def create_inbound(req: InboundReq, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin': raise HTTPException(403)
    db = SessionLocals[current_user['db_name']]()
    try:
        now_time = datetime.now()
        med = db.query(models.Medicine).filter(models.Medicine.id == req.medicine_id).first()
        inv = db.query(models.Inventory).filter(models.Inventory.warehouse_id == req.warehouse_id, models.Inventory.medicine_id == req.medicine_id).first()
        
        if not inv:
            # 如果库存表里没这行，自动创建一行
            inv = models.Inventory(warehouse_id=req.warehouse_id, medicine_id=req.medicine_id, quantity=0)
            db.add(inv)
        
        inv.quantity += req.quantity
        inv.last_updated = now_time
        
        detail = f"【入库】为 {DB_BRANCH_NAMES.get(req.warehouse_id)} 办理 {med.name} 采购入库 x{req.quantity}"
        db.add(models.AdminAction(operator_id=current_user['id'], action_type="INBOUND", details=detail, create_time=now_time))
        db.commit()
        if settings.REAL_TIME_SYNC:
            try: 
                time.sleep(1)
                sync_logic()
            except: pass
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=str(e))
    finally: db.close()

# --- 查询类接口 ---
@router.get("/admin-actions", response_model=List[AdminActionOut])
def get_admin_actions(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin': raise HTTPException(403)
    db = SessionLocals["mssql"]()
    try:
        return db.query(models.AdminAction).order_by(models.AdminAction.create_time.desc()).all()
    finally: db.close()

@router.get("/stock/{db_name}", response_model=List[StockItem])
def get_warehouse_stock(db_name: str):
    db = SessionLocals[db_name]()
    try:
        target_map = { "mysql": 1, "pg": 2, "mssql": 3 }
        target = target_map.get(db_name)
        q = db.query(models.Inventory)
        if target: q = q.filter(models.Inventory.warehouse_id == target)
        return q.all()
    finally: db.close()

@router.get("/my-records", response_model=List[AuditLogOut])
def get_my_records(current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        return db.query(models.AuditLog.create_time, models.AuditLog.operation_type, models.AuditLog.change_amount, models.AuditLog.description, models.Medicine.name.label("medicine_name")).outerjoin(models.Medicine, models.AuditLog.medicine_id == models.Medicine.id).filter(models.AuditLog.operator_id == current_user['id']).order_by(models.AuditLog.create_time.desc()).all()
    finally: db.close()

@router.get("/prescriptions", response_model=List[PrescriptionOut])
def get_prescriptions(current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        q = db.query(models.Prescription.id, models.Prescription.prescription_no, models.Prescription.patient_name, models.Prescription.total_amount, models.Prescription.create_time, models.Prescription.warehouse_id, models.Prescription.doctor_id, models.User.username.label("doctor_name")).join(models.User, models.Prescription.doctor_id == models.User.id)
        if current_user['role'] == 'branch_admin': q = q.filter(models.Prescription.warehouse_id == current_user['branch_id'])
        elif current_user['role'] != 'super_admin': q = q.filter(models.Prescription.doctor_id == current_user['id'])
        return q.order_by(models.Prescription.create_time.desc()).all()
    finally: db.close()

@router.get("/prescription/{pres_id}/items", response_model=List[PrescriptionItemOut])
def get_prescription_items(pres_id: str, current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        return db.query(models.Medicine.name.label("medicine_name"), models.PrescriptionItem.quantity, models.PrescriptionItem.price_snapshot, (models.PrescriptionItem.quantity * models.PrescriptionItem.price_snapshot).label("line_total")).join(models.Medicine, models.PrescriptionItem.medicine_id == models.Medicine.id).filter(models.PrescriptionItem.prescription_id == pres_id).all()
    finally: db.close()