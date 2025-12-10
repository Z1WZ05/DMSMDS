# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Unicode
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Medicine(Base):
    __tablename__ = 'medicines'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(100), nullable=False)
    category = Column(Unicode(50))
    price = Column(Float, nullable=False)
    danger_level = Column(Unicode(20))

class Warehouse(Base):
    __tablename__ = 'warehouses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(100), nullable=False)
    location = Column(Unicode(200))

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
    medicine_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=False)
    change_amount = Column(Integer, nullable=False)
    operation_type = Column(String(20))
    operator_id = Column(Integer)
    create_time = Column(DateTime, default=func.now())

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