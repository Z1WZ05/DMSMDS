# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 数据库连接配置 (和你之前测试成功的一致)
DB_CONFIG = {
    "mysql": "mysql+pymysql://root:RootPassword123!@127.0.0.1:33061/region_a_db",
    "pg": "postgresql+psycopg2://postgres:RootPassword123!@127.0.0.1:5432/region_b_db",
    "mssql": "mssql+pymssql://sa:RootPassword123!@127.0.0.1:14330/master?charset=utf8"
}

# 创建引擎字典 (启动时建立连接)
engines = {name: create_engine(url) for name, url in DB_CONFIG.items()}

# 创建 Session 工厂字典
SessionLocals = {name: sessionmaker(autocommit=False, autoflush=False, bind=engine) for name, engine in engines.items()}

def get_db(db_name: str):
    """
    这是一个依赖注入函数。
    它会根据传入的 db_name ('mysql', 'pg', 'mssql') 返回对应的数据库会话。
    """
    if db_name not in SessionLocals:
        raise ValueError(f"Unknown database: {db_name}")
    
    db = SessionLocals[db_name]()
    try:
        yield db
    finally:
        db.close()