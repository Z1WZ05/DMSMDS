from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Unicode
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# ==========================================
# 1. 基础字典表
# ==========================================
class Medicine(Base):
    __tablename__ = 'medicines'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(100), nullable=False)
    category = Column(Unicode(50))
    price = Column(Float, nullable=False)
    danger_level = Column(Unicode(20), nullable=False)

class Warehouse(Base):
    __tablename__ = 'warehouses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(100), nullable=False)
    location = Column(Unicode(200))

# ==========================================
# 2. 用户权限
# ==========================================
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    branch_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

# ==========================================
# 3. 业务数据 (库存 & 审计)
# ==========================================
class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, ForeignKey('medicines.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    quantity = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('warehouse_id', 'medicine_id', name='uq_warehouse_medicine'),)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, nullable=True) # 允许为空
    warehouse_id = Column(Integer, nullable=False)
    change_amount = Column(Integer, nullable=False)
    operation_type = Column(String(50)) 
    operator_id = Column(Integer)
    description = Column(Unicode(200))
    create_time = Column(DateTime, default=func.now())

# ==========================================
# 4. 处方系统 (本次新增的核心缺失部分)
# ==========================================
class Prescription(Base):
    """处方单 (主表)"""
    __tablename__ = 'prescriptions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prescription_no = Column(String(50), unique=True, nullable=False)
    patient_name = Column(Unicode(50), nullable=False)
    doctor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    total_amount = Column(Float, default=0.0)
    create_time = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

class PrescriptionItem(Base):
    """处方明细 (子表)"""
    __tablename__ = 'prescription_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prescription_id = Column(Integer, ForeignKey('prescriptions.id'), nullable=False)
    medicine_id = Column(Integer, ForeignKey('medicines.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_snapshot = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

# ==========================================
# 5. 系统辅助
# ==========================================
class AlertMessage(Base):
    __tablename__ = 'alert_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer)
    message = Column(Unicode(500))
    create_time = Column(DateTime, default=func.now())
    is_read = Column(Integer, default=0)

class SyncConflictLog(Base):
    __tablename__ = 'sync_conflict_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50))
    record_id = Column(Integer)
    source_db = Column(String(20))
    target_db = Column(String(20))
    conflict_reason = Column(Unicode(500))
    status = Column(String(20), default='PENDING')
    create_time = Column(DateTime, default=func.now())
    resolved_time = Column(DateTime, nullable=True)