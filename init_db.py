import time
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Unicode, Index
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
# 2. 用户与权限 (满足要求 b: 增加索引)
# ==========================================
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Unicode(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(Unicode(20), nullable=False)
    branch_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # 索引：加速按用户名和分院的查询
    __table_args__ = (Index('idx_user_lookup', 'username', 'branch_id'),)

# ==========================================
# 3. 业务数据 (满足要求 b: 增加性能优化索引)
# ==========================================
class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, ForeignKey('medicines.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    quantity = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('warehouse_id', 'medicine_id', name='uq_warehouse_medicine'),
        Index('idx_inventory_stock', 'warehouse_id', 'quantity'), # 加速库存预警查询
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=False)
    change_amount = Column(Integer, nullable=False)
    operation_type = Column(String(50)) 
    operator_id = Column(Integer)
    description = Column(Unicode(200))
    create_time = Column(DateTime, default=func.now())

    # 索引：满足要求 b 性能优化，加速报表统计
    __table_args__ = (Index('idx_audit_report', 'create_time', 'operation_type'),)

# ==========================================
# 4. 处方系统 (新增预警字段与复合索引)
# ==========================================
class Prescription(Base):
    __tablename__ = 'prescriptions'
    id = Column(String(36), primary_key=True)
    prescription_no = Column(String(50), unique=True, nullable=False)
    patient_name = Column(Unicode(50), nullable=False)
    doctor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    total_amount = Column(Float, default=0.0)
    
    # 【新增】风险管控字段
    is_warned = Column(Integer, default=0)    # 是否触发预警 (0:正常, 1:预警)
    doctor_note = Column(Unicode(500))         # 医生强制通过时的备注
    
    create_time = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # 索引：满足要求 b，加速“医生处方核查”页面的多维搜索
    __table_args__ = (Index('idx_pres_search', 'doctor_id', 'create_time', 'is_warned'),)

class PrescriptionItem(Base):
    __tablename__ = 'prescription_items'
    id = Column(String(36), primary_key=True)
    prescription_id = Column(String(36), ForeignKey('prescriptions.id'), nullable=False)
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
    # 类型：'RISK' (高额预警), 'STOCK' (游标生成的补货建议)
    alert_type = Column(String(20), default='RISK') 
    message = Column(Unicode(1000)) 
    create_time = Column(DateTime, default=func.now())
    is_read = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

class SyncConflictLog(Base):
    __tablename__ = 'sync_conflict_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50))
    record_id = Column(String(36)) 
    source_db = Column(String(20))
    target_db = Column(String(20))
    conflict_reason = Column(Unicode(1000))
    status = Column(String(20), default='PENDING')
    resolution_choice = Column(String(20), nullable=True)
    create_time = Column(DateTime, default=func.now())
    resolved_time = Column(DateTime, nullable=True)

class SystemSetting(Base):
    __tablename__ = 'system_settings'
    id = Column(Integer, primary_key=True)
    real_time_sync = Column(Integer, default=1)
    scheduled_sync = Column(Integer, default=1)
    sync_interval = Column(Integer, default=10)
    sender_email = Column(Unicode(100))
    smtp_password = Column(String(100))
    frontend_url = Column(String(200), default="http://localhost:5173")

class AdminAction(Base):
    __tablename__ = 'admin_actions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    operator_id = Column(Integer, nullable=False)
    action_type = Column(String(50))
    details = Column(Unicode(500))
    create_time = Column(DateTime, default=func.now())

class SyncStats(Base):
    """同步统计表 - 记录每日同步质量指标"""
    __tablename__ = 'sync_stats'
    sync_date = Column(String(10), primary_key=True) # 格式：2025-12-22
    auto_sync_count = Column(Integer, default=0)
    conflict_count = Column(Integer, default=0)
    manual_resolve_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

# 配置
DB_URLS = {
    "MySQL (Region A)": "mysql+pymysql://root:RootPassword123!@127.0.0.1:33061/region_a_db",
    "PostgreSQL (Region B)": "postgresql+psycopg2://postgres:RootPassword123!@127.0.0.1:5432/region_b_db",
    "SQL Server (Central)": "mssql+pymssql://sa:RootPassword123!@127.0.0.1:14330/master?charset=utf8"
}

def init_databases():
    print("🚀 [Init] 初始化数据库架构...")
    for db_name, db_url in DB_URLS.items():
        print(f"   正在连接: {db_name} ...")
        try:
            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            print(f"   ✅ {db_name}: 成功！")
        except Exception as e:
            print(f"   ❌ {db_name}: 失败！{e}")

if __name__ == "__main__":
    init_databases()