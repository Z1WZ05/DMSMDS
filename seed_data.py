import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from init_db import Medicine, Warehouse, Inventory, User, DB_URLS

# ==========================================
# 1. 药品字典 (严格对应权限等级)
# ==========================================
MEDICINES_DATA = [
    # --- 等级 1: 护士可开 ---
    {"name": "医用外科口罩", "category": "医疗器械", "price": 5.0, "danger_level": "无"},
    {"name": "碘伏消毒液", "category": "外用药", "price": 10.0, "danger_level": "无"},
    {"name": "999感冒灵", "category": "感冒药", "price": 16.5, "danger_level": "非处方药"},
    {"name": "布洛芬缓释胶囊", "category": "解热镇痛", "price": 32.0, "danger_level": "非处方药"},
    
    # --- 等级 2: 普通医生可开 (+护士的) ---
    {"name": "阿莫西林胶囊", "category": "抗生素", "price": 25.5, "danger_level": "处方药"},
    {"name": "头孢克肟分散片", "category": "抗生素", "price": 45.0, "danger_level": "处方药"},
    
    # --- 等级 3: 急诊医生可开 (+医生的) ---
    {"name": "硝酸甘油片", "category": "心血管", "price": 55.0, "danger_level": "处方药(急救)"},
    {"name": "盐酸佩替啶注射液", "category": "镇痛", "price": 120.0, "danger_level": "处方药(急救)"},
]

# ==========================================
# 2. 仓库字典
# ==========================================
WAREHOUSES_DATA = [
    {"name": "第一分院 (MySQL)", "location": "城南路 101 号"},
    {"name": "第二分院 (PostgreSQL)", "location": "高新大道 888 号"},
    {"name": "集团总库 (SQL Server)", "location": "物流园区 A 座"},
]

# ==========================================
# 3. 用户字典 (全员配置)
# ==========================================
# branch_id: 1=MySQL, 2=PG, 3=MSSQL
USERS_DATA = [
    # --- 分院 1 (MySQL) 团队 ---
    {"username": "nurse_1", "role": "nurse", "branch_id": 1, "password": "123"},
    {"username": "doc_1",   "role": "doctor", "branch_id": 1, "password": "123"},
    {"username": "emer_1",  "role": "emergency", "branch_id": 1, "password": "123"},
    {"username": "admin_1", "role": "branch_admin", "branch_id": 1, "password": "123"},

    # --- 分院 2 (PG) 团队 ---
    {"username": "nurse_2", "role": "nurse", "branch_id": 2, "password": "123"},
    {"username": "doc_2",   "role": "doctor", "branch_id": 2, "password": "123"},
    {"username": "emer_2",  "role": "emergency", "branch_id": 2, "password": "123"},
    {"username": "admin_2", "role": "branch_admin", "branch_id": 2, "password": "123"},

    # --- 总院 (MSSQL) 团队 ---
    {"username": "nurse_3", "role": "nurse", "branch_id": 3, "password": "123"},
    {"username": "doc_3",   "role": "doctor", "branch_id": 3, "password": "123"},
    {"username": "emer_3",  "role": "emergency", "branch_id": 3, "password": "123"},
    {"username": "super_admin", "role": "super_admin", "branch_id": 3, "password": "123"}, # 超管在总院
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

        # 3. 插入用户 (全量同步)
        if session.query(User).count() == 0:
            for u in USERS_DATA:
                session.add(User(**u))
        
        session.commit()

        # 4. 插入库存 (全量生成)
        medicines = session.query(Medicine).all()
        warehouses = session.query(Warehouse).all()

        if session.query(Inventory).count() == 0:
            count = 0
            for wh in warehouses:
                for med in medicines:
                    # 初始库存设为 100
                    inv = Inventory(medicine_id=med.id, warehouse_id=wh.id, quantity=100)
                    session.add(inv)
                    count += 1
            session.commit()
            print(f"   ✅ 已生成 {count} 条库存记录，12 个测试账号。")
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
    print("\n🎉 数据库角色与权限数据重构完成！")