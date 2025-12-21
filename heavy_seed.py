import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from init_db import Medicine, Warehouse, Inventory, User, Prescription, PrescriptionItem, DB_URLS

# 加密配置
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
DEFAULT_PWD_HASH = pwd_context.hash("123")

# ==========================================
# 1. 真实药品名录 (45 种)
# ==========================================
DRUG_LIST = [
    ("阿莫西林胶囊", "抗生素", 28.5, "处方药"),
    ("左氧氟沙星片", "抗生素", 35.0, "处方药"),
    ("罗红霉素分散片", "抗生素", 22.8, "处方药"),
    ("头孢克肟胶囊", "抗生素", 45.0, "处方药"),
    ("阿奇霉素干混悬剂", "抗生素", 38.2, "处方药"),
    ("布洛芬缓释胶囊", "解热镇痛", 25.0, "非处方药"),
    ("对乙酰氨基酚片", "感冒用药", 12.5, "无"),
    ("999感冒灵颗粒", "感冒用药", 18.0, "无"),
    ("连花清瘟胶囊", "中成药", 29.5, "非处方药"),
    ("复方氨酚烷胺片", "感冒用药", 15.0, "无"),
    ("硝酸甘油片", "心血管", 16.5, "处方药(急救)"),
    ("阿司匹林肠溶片", "心血管", 19.8, "处方药"),
    ("地高辛片", "心血管", 42.0, "处方药(急救)"),
    ("酒石酸美托洛尔片", "心血管", 33.5, "处方药"),
    ("多巴胺注射液", "急救用药", 95.0, "处方药(急救)"),
    ("奥美拉唑肠溶胶囊", "消化系统", 48.5, "处方药"),
    ("多潘立酮片(吗丁啉)", "消化系统", 32.0, "非处方药"),
    ("蒙脱石散", "消化系统", 15.5, "无"),
    ("铝碳酸镁咀嚼片", "消化系统", 28.0, "无"),
    ("二甲双胍缓释片", "糖尿病", 26.0, "处方药"),
    ("格列齐特片", "糖尿病", 31.5, "处方药"),
    ("阿卡波糖片", "糖尿病", 65.0, "处方药"),
    ("维生素C泡腾片", "营养补充", 12.0, "无"),
    ("葡萄糖酸钙口服液", "营养补充", 45.0, "无"),
    ("医用外科口罩", "医疗器械", 1.5, "无"),
    ("酒精消毒液(500ml)", "医疗器械", 8.5, "无"),
    ("无菌医用棉签", "医疗器械", 3.0, "无"),
    ("磷酸奥司他韦颗粒", "抗病毒", 85.0, "处方药"),
    ("布地奈德混悬液", "呼吸系统", 120.0, "处方药"),
    ("孟鲁司特钠咀嚼片", "呼吸系统", 58.0, "处方药"),
    ("氯雷他定片", "抗过敏", 21.0, "无"),
    ("地塞米松磷酸钠", "激素类", 15.0, "处方药(急救)"),
    ("盐酸吗啡缓释片", "镇痛类", 155.0, "处方药(急救)"),
    ("间苯三酚注射液", "妇科用药", 45.0, "处方药"),
    ("氨溴索口服溶液", "呼吸系统", 18.5, "无"),
    ("曲安奈德益康唑乳膏", "皮肤用药", 24.0, "无"),
    ("莫匹罗星软膏", "皮肤用药", 32.5, "非处方药"),
    ("利尿灵(呋塞米)", "利尿剂", 12.0, "处方药"),
    ("螺内酯片", "利尿剂", 25.5, "处方药"),
    ("复方丹参滴丸", "中成药", 38.0, "无"),
    ("稳心颗粒", "中成药", 42.0, "无"),
    ("生脉饮", "中成药", 22.0, "无"),
    ("板蓝根颗粒", "中成药", 15.0, "无"),
    ("开塞露", "便秘用药", 2.0, "无"),
    ("红霉素眼膏", "五官用药", 5.5, "无")
]

def run_heavy_seed():
    print("🐘 正在执行[全量数据同步]重型注入...")
    
    # 2000条处方作为样本
    TOTAL_PRESCRIPTIONS = 2000 
    
    # 获取公共时间戳基准（抹掉微秒防止不一致）
    sync_time = datetime.now().replace(microsecond=0)

    for db_name, db_url in DB_URLS.items():
        print(f"\n💉 正在处理数据库: [{db_name}]")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # A. 彻底清空（级联顺序）
            print("   - 正在物理清空旧业务数据...")
            session.execute(text("DELETE FROM alert_messages"))
            session.execute(text("DELETE FROM prescription_items"))
            session.execute(text("DELETE FROM prescriptions"))
            session.execute(text("DELETE FROM inventory"))
            session.execute(text("DELETE FROM medicines"))
            session.commit()

            # B. 重置自增 ID (可选，增强鲁棒性)
            try:
                if "MySQL" in db_name: session.execute(text("ALTER TABLE medicines AUTO_INCREMENT = 1"))
                elif "Postgres" in db_name: session.execute(text("TRUNCATE medicines RESTART IDENTITY CASCADE"))
                elif "SQL Server" in db_name: session.execute(text("DBCC CHECKIDENT ('medicines', RESEED, 0)"))
                session.commit()
            except: pass

            # C. 注入药品并获取真实 ID
            print("   - 注入 45 种药品...")
            medicine_objects = []
            for name, cat, price, level in DRUG_LIST:
                m = Medicine(name=name, category=cat, price=price, danger_level=level)
                session.add(m)
                medicine_objects.append(m)
            session.commit() # 提交以生成 ID

            # 【关键】从数据库读取真实分配的 ID 及其价格，建立映射
            real_medicines = session.query(Medicine.id, Medicine.price).all()
            # 格式：{id: price}
            med_info_map = {m.id: m.price for m in real_medicines}
            med_ids = list(med_info_map.keys())

            # D. 初始化 Inventory (每种药每个分院 100 个)
            print("   - 正在初始化全院 100 基础库存...")
            for wh_id in [1, 2, 3]:
                for m_id in med_ids:
                    session.add(Inventory(medicine_id=m_id, warehouse_id=wh_id, quantity=100, last_updated=sync_time))
            session.commit()

            # E. 批量注入处方 (使用真实 ID)
            print(f"   - 正在生成 {TOTAL_PRESCRIPTIONS} 条符合外键约束的处方...")
            doctor_ids = [r.id for r in session.query(User.id).all()]
            
            for i in range(TOTAL_PRESCRIPTIONS):
                p_id = str(uuid.uuid4())
                # 模拟过去半年的均匀分布
                p_time = sync_time - timedelta(minutes=i * 60) 
                wh_id = random.randint(1, 3)
                doc_id = random.choice(doctor_ids)

                total_amount = 0
                items_to_add = []
                # 每张处方随机 1-3 种药
                for _ in range(random.randint(1, 3)):
                    m_id = random.choice(med_ids)
                    qty = random.randint(1, 3)
                    price = med_info_map[m_id]
                    total_amount += price * qty
                    
                    items_to_add.append(PrescriptionItem(
                        id=str(uuid.uuid4()),
                        prescription_id=p_id,
                        medicine_id=m_id,
                        quantity=qty,
                        price_snapshot=price,
                        last_updated=p_time
                    ))
                
                pres_header = Prescription(
                    id=p_id,
                    prescription_no=f"RX-{p_time.strftime('%Y%m%d')}-{i:05d}",
                    patient_name=f"患者-{random.randint(100, 999)}",
                    doctor_id=doc_id,
                    warehouse_id=wh_id,
                    total_amount=round(total_amount, 2),
                    is_warned=1 if total_amount > 2000 else 0,
                    create_time=p_time,
                    last_updated=p_time
                )
                session.add(pres_header)
                for item in items_to_add: session.add(item)

                if i % 500 == 0:
                    session.commit()
                    print(f"     已写入 {i} 条...")

            session.commit()
            print(f"   ✅ {db_name} 成功：药品、100库存、处方流水。")

        except Exception as e:
            session.rollback()
            print(f"   ❌ {db_name} 注入失败: {e}")
        finally:
            session.close()

    print("\n🎉 数据注入任务圆满完成！外键与库存逻辑已对齐。")

if __name__ == "__main__":
    run_heavy_seed()