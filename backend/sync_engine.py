import time
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from .database import SessionLocals
from . import models

scheduler = BackgroundScheduler()

# 定义所有节点
ALL_DBS = ["mysql", "pg", "mssql"]

# 定义数据归属 (Warehouse ID -> 负责的 DB Name)
OWNER_MAP = {
    1: "mysql", # 仓库1 归 MySQL 管
    2: "pg",    # 仓库2 归 PG 管
    3: "mssql"  # 仓库3 归 MSSQL 管
}

# 定义用户归属 (Branch ID -> 负责的 DB Name)
USER_OWNER_MAP = {
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
    mapper = inspect(model_class)
    for column in mapper.attrs:
        prop_name = column.key
        if prop_name == 'last_updated': continue
        if getattr(obj1, prop_name) != getattr(obj2, prop_name):
            return False
    return True

def sync_logic():
    """
    全网广播式同步逻辑
    """
    # 遍历所有数据库作为 'Source'
    for source_db_name in ALL_DBS:
        source_session = get_db_session(source_db_name)
        try:
            # 1. 同步 Inventory
            items = source_session.query(models.Inventory).all()
            for item in items:
                # 判断这个 item 是不是 source_db 拥有的
                # 如果 source_db 是 mysql，它只负责 warehouse_id=1 的数据
                owner_db = OWNER_MAP.get(item.warehouse_id)
                
                # 情况 A: 我是 Owner (我是源头)
                if owner_db == source_db_name:
                    # 遍历其他所有数据库，把我的数据推过去
                    for target_db_name in ALL_DBS:
                        if target_db_name == source_db_name: continue
                        
                        target_session = get_db_session(target_db_name)
                        try:
                            target_item = target_session.query(models.Inventory).filter(models.Inventory.id == item.id).first()
                            
                            if not target_item:
                                # 目标没有 -> 插入
                                new_data = {c.key: getattr(item, c.key) for c in inspect(models.Inventory).attrs}
                                target_session.add(models.Inventory(**new_data))
                                print(f"➕ [广播] {source_db_name} -> {target_db_name} (新增 ID:{item.id})")
                            
                            elif item.last_updated > target_item.last_updated:
                                # 我比目标新 -> 覆盖目标
                                if not models_are_equal(item, target_item, models.Inventory):
                                    for c in inspect(models.Inventory).attrs:
                                        setattr(target_item, c.key, getattr(item, c.key))
                                    print(f"⬆️ [广播] {source_db_name} -> {target_db_name} (更新 ID:{item.id})")
                                else:
                                    target_item.last_updated = item.last_updated # 静默同步时间
                            
                            elif target_item.last_updated > item.last_updated:
                                # 目标比我还新？-> 冲突！(有人改了副本)
                                if not models_are_equal(item, target_item, models.Inventory):
                                    reason = f"冲突! {source_db_name}拥有ID:{item.id}写权限，但在 {target_db_name} 发现更新的数据。"
                                    log_conflict("inventory", item.id, source_db_name, target_db_name, reason)
                                    
                            target_session.commit()
                        except Exception:
                            target_session.rollback()
                        finally:
                            target_session.close()

            # 2. 同步 Users (逻辑同上，只是归属权字段不同)
            users = source_session.query(models.User).all()
            for u in users:
                owner_db = USER_OWNER_MAP.get(u.branch_id)
                
                if owner_db == source_db_name:
                    for target_db_name in ALL_DBS:
                        if target_db_name == source_db_name: continue
                        target_session = get_db_session(target_db_name)
                        try:
                            target_u = target_session.query(models.User).filter(models.User.id == u.id).first()
                            if not target_u:
                                new_data = {c.key: getattr(u, c.key) for c in inspect(models.User).attrs}
                                target_session.add(models.User(**new_data))
                                print(f"➕ [广播] {source_db_name} -> {target_db_name} (新用户:{u.username})")
                            elif u.last_updated > target_u.last_updated:
                                if not models_are_equal(u, target_u, models.User):
                                    for c in inspect(models.User).attrs:
                                        setattr(target_u, c.key, getattr(u, c.key))
                                    print(f"⬆️ [广播] {source_db_name} -> {target_db_name} (更新用户:{u.username})")
                                else:
                                    target_u.last_updated = u.last_updated
                            elif target_u.last_updated > u.last_updated:
                                if not models_are_equal(u, target_u, models.User):
                                    reason = f"冲突! 用户 {u.username} 归属 {source_db_name}，但在 {target_db_name} 被修改。"
                                    log_conflict("users", u.id, source_db_name, target_db_name, reason)
                            target_session.commit()
                        except:
                            target_session.rollback()
                        finally:
                            target_session.close()

        finally:
            source_session.close()

def start_sync_job():
    scheduler.add_job(sync_logic, 'interval', seconds=10)
    scheduler.start()
    print("🚀 全网广播同步引擎已启动...")