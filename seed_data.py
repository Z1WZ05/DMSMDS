import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# 引入 Unicode 修复后的模型
from init_db import Medicine, Warehouse, Inventory, DB_URLS

# 模拟基础数据
MEDICINES_DATA = [
    {"name": "阿莫西林胶囊", "category": "抗生素", "price": 25.5, "danger_level": "处方药"},
    {"name": "布洛芬缓释胶囊", "category": "解热镇痛", "price": 32.0, "danger_level": "非处方药"},
    {"name": "连花清瘟颗粒", "category": "中成药", "price": 18.0, "danger_level": "非处方药"},
    {"name": "头孢克肟分散片", "category": "抗生素", "price": 45.0, "danger_level": "处方药"},
    {"name": "云南白药气雾剂", "category": "外用药", "price": 68.0, "danger_level": "非处方药"},
    {"name": "硝酸甘油片", "category": "心血管", "price": 55.0, "danger_level": "处方药(急救)"},
    {"name": "蒙脱石散", "category": "消化系统", "price": 15.0, "danger_level": "非处方药"},
    {"name": "碘伏消毒液", "category": "外用药", "price": 10.0, "danger_level": "非处方药"},
    {"name": "医用外科口罩(10片)", "category": "医疗器械", "price": 5.0, "danger_level": "无"},
    {"name": "999感冒灵", "category": "感冒药", "price": 16.5, "danger_level": "非处方药"},
]

WAREHOUSES_DATA = [
    {"name": "第一分院 (MySQL)", "location": "城南路 101 号"},
    {"name": "第二分院 (PostgreSQL)", "location": "高新大道 888 号"},
    {"name": "集团总库 (SQL Server)", "location": "物流园区 A 座"},
]

def seed_database(db_name, db_url):
    print(f"\n🌱 正在为 [{db_name}] 注入全量数据...")
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 插入药品 (Medicines)
        if session.query(Medicine).count() == 0:
            print(f"   - 插入药品字典...")
            for m in MEDICINES_DATA:
                session.add(Medicine(**m))
        
        # 2. 插入仓库 (Warehouses)
        if session.query(Warehouse).count() == 0:
            print(f"   - 插入仓库字典...")
            for w in WAREHOUSES_DATA:
                session.add(Warehouse(**w))
        
        session.commit()

        # 3. 插入库存 (Inventory)
        # 【修改点】：不再区分数据库，所有库都生成所有仓库的数据
        medicines = session.query(Medicine).all()
        warehouses = session.query(Warehouse).all()

        if session.query(Inventory).count() == 0:
            count = 0
            print("   - 生成全量库存数据 (所有分院)...")
            for wh in warehouses:
                for med in medicines:
                    # 为了让初始状态一致，我们使用固定算法生成数量
                    # 比如：数量 = (药ID + 仓库ID) * 10
                    # 这样保证 MySQL 和 PG 里的初始数据是一模一样的
                    initial_qty = (med.id + wh.id) * 10
                    
                    inv = Inventory(
                        medicine_id=med.id, 
                        warehouse_id=wh.id, 
                        quantity=initial_qty
                    )
                    session.add(inv)
                    count += 1
            session.commit()
            print(f"✅ 成功插入 {count} 条库存记录。")
        else:
            print("   - 库存表已有数据，跳过。")

    except Exception as e:
        session.rollback()
        print(f"❌ 发生错误: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    for name, url in DB_URLS.items():
        seed_database(name, url)
    print("\n🎉 所有数据库已同步为[全量同构]状态！")