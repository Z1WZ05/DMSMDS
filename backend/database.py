import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_db_url(db_alias, db_name_in_db):
    """
    自适应获取连接地址：
    1. 如果在 Docker 容器内运行 (环境变量 IS_DOCKER=true)，使用服务名和 3306/5432/1433
    2. 如果在宿主机运行，使用 127.0.0.1 和 映射端口 (33061/14330)
    """
    
    is_docker = os.getenv("IS_DOCKER", "false").lower() == "true"

    if is_docker:
        # 【Docker 内部通信】
        # 注意：地址是 docker-compose 里的服务名，端口是容器内部端口
        if db_alias == "mysql":
            return f"mysql+pymysql://root:RootPassword123!@db_mysql:3306/{db_name_in_db}?charset=utf8mb4"
        elif db_alias == "pg":
            return f"postgresql+psycopg2://postgres:RootPassword123!@db_pg:5432/{db_name_in_db}?options=-c%20timezone=Asia/Shanghai"
        elif db_alias == "mssql":
            # SQL Server 在容器内默认也是 1433
            return f"mssql+pymssql://sa:RootPassword123!@db_mssql:1433/master?charset=utf8"
    else:
        # 【外部宿主机调试】
        if db_alias == "mysql":
            return f"mysql+pymysql://root:RootPassword123!@127.0.0.1:33061/{db_name_in_db}?charset=utf8mb4"
        elif db_alias == "pg":
            return f"postgresql+psycopg2://postgres:RootPassword123!@127.0.0.1:5432/{db_name_in_db}?options=-c%20timezone=Asia/Shanghai"
        elif db_alias == "mssql":
            return f"mssql+pymssql://sa:RootPassword123!@127.0.0.1:14330/master?charset=utf8"

DB_URLS = {
    "mysql": get_db_url("mysql", "region_a_db"),
    "pg": get_db_url("pg", "region_b_db"),
    "mssql": get_db_url("mssql", "master")
}

# 建立连接引擎，增加断线重连和心跳
engines = {
    name: create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300
    ) for name, url in DB_URLS.items()
}

SessionLocals = {name: sessionmaker(autocommit=False, autoflush=False, bind=engine) for name, engine in engines.items()}

def get_db(db_name: str):
    if db_name not in SessionLocals:
        raise ValueError(f"Unknown database: {db_name}")
    db = SessionLocals[db_name]()
    try:
        yield db
    finally:
        db.close()