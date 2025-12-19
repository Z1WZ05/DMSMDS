import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from init_db import Medicine, Warehouse, Inventory, User, DB_URLS

# 配置密码哈希工具
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# ==========================================
# 1. 基础数据准备
# ==========================================

MEDICINES_DATA = [
    {"name": "医用外科口罩", "category": "医疗器械", "price": 5.0, "danger_level": "无"},
    {"name": "碘伏消毒液", "category": "外用药", "price": 10.0, "danger_level": "无"},
    {"name": "999感冒灵", "category": "感冒药", "price": 16.5, "danger_level": "非处方药"},
    {"name": "布洛芬缓释胶囊", "category": "解热镇痛", "price": 32.0, "danger_level": "非处方药"},
    {"name": "阿莫西林胶囊", "category": "抗生素", "price": 25.5, "danger_level": "处方药"},
    {"name": "头孢克肟分散片", "category": "抗生素", "price": 45.0, "danger_level": "处方药"},
    {"name": "硝酸甘油片", "category": "心血管", "price": 55.0, "danger_level": "处方药(急救)"},
    {"name": "盐酸佩替啶注射液", "category": "镇痛", "price": 120.0, "danger_level": "处方药(急救)"},
]

WAREHOUSES_DATA = [
    {"name": "第一分院 (MySQL)", "location": "城南路 101 号"},
    {"name": "第二分院 (PostgreSQL)", "location": "高新大道 888 号"},
    {"name": "集团总库 (SQL Server)", "location": "物流园区 A 座"},
]

# 用户密码统一设为 "123"
DEFAULT_PASSWORD_HASH = get_password_hash("123")

USERS_DATA = [
    # --- 分院 1 (MySQL) 团队 ---
    {"username": "nurse_1", "role": "nurse", "branch_id": 1, "password": DEFAULT_PASSWORD_HASH},
    {"username": "doc_1",   "role": "doctor", "branch_id": 1, "password": DEFAULT_PASSWORD_HASH},
    {"username": "emer_1",  "role": "emergency", "branch_id": 1, "password": DEFAULT_PASSWORD_HASH},
    {"username": "admin_1", "role": "branch_admin", "branch_id": 1, "password": DEFAULT_PASSWORD_HASH},

    # --- 分院 2 (PG) 团队 ---
    {"username": "nurse_2", "role": "nurse", "branch_id": 2, "password": DEFAULT_PASSWORD_HASH},
    {"username": "doc_2",   "role": "doctor", "branch_id": 2, "password": DEFAULT_PASSWORD_HASH},
    {"username": "emer_2",  "role": "emergency", "branch_id": 2, "password": DEFAULT_PASSWORD_HASH},
    {"username": "admin_2", "role": "branch_admin", "branch_id": 2, "password": DEFAULT_PASSWORD_HASH},

    # --- 总院 (MSSQL) 团队 ---
    {"username": "nurse_3", "role": "nurse", "branch_id": 3, "password": DEFAULT_PASSWORD_HASH},
    {"username": "doc_3",   "role": "doctor", "branch_id": 3, "password": DEFAULT_PASSWORD_HASH},
    {"username": "emer_3",  "role": "emergency", "branch_id": 3, "password": DEFAULT_PASSWORD_HASH},
    {"username": "super_admin", "role": "super_admin", "branch_id": 3, "password": DEFAULT_PASSWORD_HASH},
]

def seed_database(db_name, db_url):
    print(f"\n🌱 [{db_name}] 正在注入全量数据...")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 插入药品
        if session.query(Medicine).count() == 0:
            for m in MEDICINES_DATA:
                session.add(Medicine(**m))
        
        # 2. 插入仓库
        if session.query(Warehouse).count() == 0:
            for w in WAREHOUSES_DATA:
                session.add(Warehouse(**w))

        # 3. 插入用户 (带Hash密码)
        if session.query(User).count() == 0:
            for u in USERS_DATA:
                session.add(User(**u))
        
        session.commit()

        # 4. 插入库存 (生成所有仓库的数据)
        medicines = session.query(Medicine).all()
        warehouses = session.query(Warehouse).all()

        if session.query(Inventory).count() == 0:
            count = 0
            for wh in warehouses:
                for med in medicines:
                    # 初始库存设为 100
                    inv = Inventory(
                        medicine_id=med.id, 
                        warehouse_id=wh.id, 
                        quantity=100
                    )
                    session.add(inv)
                    count += 1
            session.commit()
            print(f"   ✅ 成功：药品、仓库、用户(12个)、库存({count}条)。")
        else:
            print("   - 数据已存在，跳过。")

    except Exception as e:
        session.rollback()
        print(f"   ❌ 错误: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    for name, url in DB_URLS.items():
        seed_database(name, url)
    print("\n🎉 全局数据初始化完成！密码均为 123")