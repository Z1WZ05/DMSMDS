import time
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Unicode
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# ==========================================
# 1. 基础字典表 (Master Data)
# ==========================================

class Medicine(Base):
    """药品信息表"""
    __tablename__ = 'medicines'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(100), nullable=False)
    category = Column(Unicode(50))
    price = Column(Float, nullable=False)
    # 危险等级: '无', '处方药', '处方药(急救)'
    danger_level = Column(Unicode(20), nullable=False)

class Warehouse(Base):
    """仓库/分院信息表"""
    __tablename__ = 'warehouses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(100), nullable=False)
    location = Column(Unicode(200))

# ==========================================
# 2. 用户与权限表 (RBAC Core)
# ==========================================

class User(Base):
    """用户信息表"""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False) # 存储哈希后的密码
    
    # 角色: nurse, doctor, emergency, branch_admin, super_admin
    role = Column(String(20), nullable=False)
    
    # 所属分院ID: 关联 warehouses.id
    branch_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    
    # 【关键新增】用于同步的时间戳，确保用户数据的变更能被同步引擎捕捉
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

# ==========================================
# 3. 业务数据表 (Transaction Data)
# ==========================================

class Inventory(Base):
    """库存表"""
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, ForeignKey('medicines.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    quantity = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # 联合唯一索引：确保一个仓库一种药只有一条记录
    __table_args__ = (
        UniqueConstraint('warehouse_id', 'medicine_id', name='uq_warehouse_medicine'),
    )

class AuditLog(Base):
    """审计日志表 (记录开药、调拨等操作历史)"""
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=False)
    change_amount = Column(Integer, nullable=False) # 负数代表消耗，正数代表入库
    operation_type = Column(String(20))             # PRESCRIBE(开药), ALLOCATE(调拨)
    operator_id = Column(Integer)                   # 操作员(User.id)
    create_time = Column(DateTime, default=func.now())

class AlertMessage(Base):
    """预警消息表 (配合数据库游标/存储过程使用)"""
    __tablename__ = 'alert_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer)
    message = Column(Unicode(500)) # 具体的报警内容
    create_time = Column(DateTime, default=func.now())
    is_read = Column(Integer, default=0)

class SyncConflictLog(Base):
    """同步冲突日志表"""
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

# ==========================================
# 4. 连接配置
# ==========================================
DB_URLS = {
    "MySQL (Region A)": "mysql+pymysql://root:RootPassword123!@127.0.0.1:33061/region_a_db",
    "PostgreSQL (Region B)": "postgresql+psycopg2://postgres:RootPassword123!@127.0.0.1:5432/region_b_db",
    "SQL Server (Central)": "mssql+pymssql://sa:RootPassword123!@127.0.0.1:14330/master?charset=utf8"
}

def init_databases():
    print("🚀 [Init] 开始初始化数据库架构...")
    for db_name, db_url in DB_URLS.items():
        print(f"   正在连接: {db_name} ...")
        try:
            engine = create_engine(db_url)
            # 这会自动创建所有表，如果表已存在且结构没变则忽略
            # 建议在运行前先在 DBeaver 里 Drop 所有表，以确保结构最新
            Base.metadata.create_all(engine)
            print(f"   ✅ {db_name}: 表结构创建成功！")
        except Exception as e:
            print(f"   ❌ {db_name}: 失败！原因: {e}")

if __name__ == "__main__":
    init_databases()