import time
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from .database import SessionLocals
from . import models

scheduler = BackgroundScheduler()

# 定义所有数据库节点
ALL_DBS = ["mysql", "pg", "mssql"]

# 定义数据归属 (ID -> 负责的 DB Name)
# 1=分院1(MySQL), 2=分院2(PG), 3=总院(MSSQL)
OWNER_MAP = {
    1: "mysql", 
    2: "pg",    
    3: "mssql"  
}

def get_db_session(db_name):
    return SessionLocals[db_name]()

def log_conflict(table, record_id, owner_db, intruder_db, reason):
    """记录冲突到总库"""
    mssql = SessionLocals["mssql"]()
    try:
        exists = mssql.query(models.SyncConflictLog).filter(
            models.SyncConflictLog.record_id == record_id,
            models.SyncConflictLog.table_name == table,
            models.SyncConflictLog.status == 'PENDING'
        ).first()
        
        if not exists:
            print(f"📧 [冲突报警] {reason}")
            conflict = models.SyncConflictLog(
                table_name=table,
                record_id=record_id,
                source_db=owner_db,
                target_db=intruder_db,
                conflict_reason=reason,
                status='PENDING'
            )
            mssql.add(conflict)
            mssql.commit()
    finally:
        mssql.close()

def models_are_equal(obj1, obj2, model_class):
    """比较内容是否一致 (忽略时间戳)"""
    mapper = inspect(model_class)
    for column in mapper.attrs:
        prop_name = column.key
        if prop_name == 'last_updated': continue
        # 对于外键对象等特殊字段跳过
        if prop_name.startswith('_'): continue
        
        val1 = getattr(obj1, prop_name)
        val2 = getattr(obj2, prop_name)
        if val1 != val2:
            return False
    return True

def sync_logic():
    """
    【核心】全网广播同步引擎
    遍历核心业务表，自动识别数据归属，进行广播或冲突检测
    """
    # 定义需要同步的模型列表
    # 注意：PrescriptionItem 作为子表，通常随主表查询，但为了简单这里也独立同步
    sync_models = [models.User, models.Inventory, models.Prescription, models.PrescriptionItem]

    for model_class in sync_models:
        table_name = model_class.__tablename__
        
        # 遍历所有数据库作为 '潜在源头'
        for source_db_name in ALL_DBS:
            source_session = get_db_session(source_db_name)
            try:
                # 取出该库所有数据
                items = source_session.query(model_class).all()
                
                for item in items:
                    # 1. 判断数据归属权
                    owner_id = -1
                    if hasattr(item, 'branch_id'):
                        owner_id = item.branch_id
                    elif hasattr(item, 'warehouse_id'):
                        owner_id = item.warehouse_id
                    elif hasattr(item, 'prescription_id'):
                        # 子表归属权稍微复杂点，暂且认为是跟随主表的 warehouse_id
                        # 为简化实验，假设子表不冲突，或者通过 PRESCRIPTION_ID 的前缀/关联查询判断
                        # 这里做一个简化：如果当前库是 mysql，就认为它拥有的子表也是 mysql 的 (仅用于演示)
                        # 更严谨的做法是 join 主表查 warehouse_id，但太复杂。
                        # 我们利用 DB_URLS 的映射逻辑：如果是在 mysql 库里查到的，暂且当做它是源
                        owner_id = 1 if source_db_name == 'mysql' else (2 if source_db_name == 'pg' else 3)
                    
                    owner_db = OWNER_MAP.get(owner_id)

                    # 2. 如果当前数据库 就是 数据的拥有者 (Owner)
                    if owner_db == source_db_name:
                        # 向其他所有数据库广播
                        for target_db_name in ALL_DBS:
                            if target_db_name == source_db_name: continue
                            
                            target_session = get_db_session(target_db_name)
                            try:
                                target_item = target_session.query(model_class).filter(model_class.id == item.id).first()
                                
                                if not target_item:
                                    # [新增广播]
                                    new_data = {c.key: getattr(item, c.key) for c in inspect(model_class).attrs if c.key != 'id'}
                                    # 显式设置ID以保持一致
                                    new_obj = model_class(id=item.id, **new_data)
                                    target_session.add(new_obj)
                                    print(f"➕ [同步] {table_name}:{item.id} {source_db_name}->{target_db_name}")
                                
                                elif item.last_updated > target_item.last_updated:
                                    # [更新广播]
                                    if not models_are_equal(item, target_item, model_class):
                                        for c in inspect(model_class).attrs:
                                            if c.key != 'id':
                                                setattr(target_item, c.key, getattr(item, c.key))
                                        print(f"⬆️ [更新] {table_name}:{item.id} {source_db_name}->{target_db_name}")
                                    else:
                                        target_item.last_updated = item.last_updated # 静默同步时间
                                
                                elif target_item.last_updated > item.last_updated:
                                    # [逆向冲突] 目标库(非Owner)竟然比源库(Owner)还新
                                    if not models_are_equal(item, target_item, model_class):
                                        reason = f"冲突! {source_db_name}拥有{table_name}:{item.id}权限，但在 {target_db_name} 发现修改。"
                                        log_conflict(table_name, item.id, source_db_name, target_db_name, reason)
                                
                                target_session.commit()
                            except Exception:
                                target_session.rollback()
                            finally:
                                target_session.close()
            finally:
                source_session.close()

def start_sync_job():
    # 只需要添加这一个任务，它会自己循环处理所有表
    scheduler.add_job(sync_logic, 'interval', seconds=10)
    scheduler.start()
    print("🚀 全能同步引擎已启动 (User/Inventory/Prescription)...")