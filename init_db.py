import time
# 【修改1】引入 Unicode 类型
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Unicode
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# ==========================================
# 1. 定义表结构 (修改 String -> Unicode)
# ==========================================

class Medicine(Base):
    __tablename__ = 'medicines'
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 【修改2】凡是可能存中文的，都改成 Unicode
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

    __table_args__ = (
        UniqueConstraint('warehouse_id', 'medicine_id', name='uq_warehouse_medicine'),
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=False)
    change_amount = Column(Integer, nullable=False)
    operation_type = Column(String(20)) # 这个是代码(IN/OUT)，用 String 没问题
    operator_id = Column(Integer)
    create_time = Column(DateTime, default=func.now())

class SyncConflictLog(Base):
    __tablename__ = 'sync_conflict_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50))
    record_id = Column(Integer)
    source_db = Column(String(20))
    target_db = Column(String(20))
    conflict_reason = Column(Unicode(500)) # 原因里可能有中文
    status = Column(String(20), default='PENDING')
    create_time = Column(DateTime, default=func.now())
    resolved_time = Column(DateTime, nullable=True)

# ==========================================
# 2. 数据库连接配置
# ==========================================
DB_URLS = {
    "MySQL (Region A)": "mysql+pymysql://root:RootPassword123!@127.0.0.1:33061/region_a_db",
    "PostgreSQL (Region B)": "postgresql+psycopg2://postgres:RootPassword123!@127.0.0.1:5432/region_b_db",
    # 【修改3】在 SQL Server 连接串末尾加上 ?charset=utf8
    "SQL Server (Central)": "mssql+pymssql://sa:RootPassword123!@127.0.0.1:14330/master?charset=utf8"
}

def init_databases():
    print("🚀 开始修复并初始化数据库...")
    for db_name, db_url in DB_URLS.items():
        print(f"正在连接: {db_name} ...")
        try:
            engine = create_engine(db_url)
            # 这一步会自动创建 NVARCHAR 类型的列
            Base.metadata.create_all(engine)
            print(f"✅ {db_name}: 表结构重建成功！")
        except Exception as e:
            print(f"❌ {db_name}: 失败！原因: {e}")

if __name__ == "__main__":
    init_databases()