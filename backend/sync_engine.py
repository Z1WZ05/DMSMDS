import time
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from .database import SessionLocals
from . import models

scheduler = BackgroundScheduler()

def get_db_session(db_name):
    return SessionLocals[db_name]()

def log_conflict(db_session, table, record_id, src_db, tgt_db, reason):
    """记录冲突"""
    exists = db_session.query(models.SyncConflictLog).filter(
        models.SyncConflictLog.record_id == record_id,
        models.SyncConflictLog.table_name == table,
        models.SyncConflictLog.status == 'PENDING'
    ).first()
    
    if not exists:
        print(f"📧 [模拟发送邮件] 冲突报警: {reason}")
        conflict = models.SyncConflictLog(
            table_name=table,
            record_id=record_id,
            source_db=src_db,
            target_db=tgt_db,
            conflict_reason=reason,
            status='PENDING'
        )
        db_session.add(conflict)
        db_session.commit()

def sync_branch_logic(branch_db_name: str, branch_cn_name: str, my_warehouse_id: int):
    """
    分院与总院的同步逻辑 (全量数据版)
    :param my_warehouse_id: 当前分院拥有写权限的仓库ID (如 MySQL 是 1)
    """
    # print(f"🔄 同步检查: {branch_cn_name} <-> 总院")
    
    branch_db = get_db_session(branch_db_name)
    central_db = get_db_session("mssql")
    
    try:
        # 获取分院所有库存
        branch_items = branch_db.query(models.Inventory).all()
        
        for b_item in branch_items:
            # 在总院找对应记录
            c_item = central_db.query(models.Inventory).filter(
                models.Inventory.warehouse_id == b_item.warehouse_id,
                models.Inventory.medicine_id == b_item.medicine_id
            ).first()
            
            if not c_item:
                # 理论上 seed_data 保证了一致，这里是防止意外
                continue

            # =================================================
            # 策略 A: 处理 "我自己的" 仓库数据 (Read-Write)
            # =================================================
            if b_item.warehouse_id == my_warehouse_id:
                # 1. 正常上传: 我比总院新 -> 更新总院
                if b_item.last_updated > c_item.last_updated:
                    c_item.quantity = b_item.quantity
                    c_item.last_updated = b_item.last_updated
                    print(f"⬆️ [上传] {branch_cn_name}更新了自家库存 -> 同步到总院 (ID: {b_item.id})")
                
                # 2. 冲突检测: 总院竟然比我还新? -> 报警
                elif c_item.last_updated > b_item.last_updated:
                    if c_item.quantity != b_item.quantity:
                        reason = f"冲突! {branch_cn_name}自家库存被总院修改. 本地:{b_item.quantity} vs 远端:{c_item.quantity}"
                        print(f"⚠️ {reason}")
                        log_conflict(central_db, "inventory", b_item.id, branch_db_name, "mssql", reason)

            # =================================================
            # 策略 B: 处理 "别人的" 仓库数据 (Read-Only)
            # =================================================
            else:
                # 逻辑: 无条件信任总院 (因为那是别人改的，经过总院传过来的)
                if c_item.last_updated > b_item.last_updated:
                    # 更新本地的分院数据库
                    b_item.quantity = c_item.quantity
                    b_item.last_updated = c_item.last_updated
                    # 注意：这里需要 commit branch_db
                    branch_db.commit() 
                    print(f"⬇️ [下载] {branch_cn_name}同步了其他分院数据 (Warehouse {b_item.warehouse_id})")

        # 提交对总院的修改
        central_db.commit()
        
    except Exception as e:
        print(f"❌ 同步出错: {e}")
        central_db.rollback()
        branch_db.rollback()
    finally:
        branch_db.close()
        central_db.close()

def start_sync_job():
    # MySQL 是第一分院，只负责 Warehouse ID = 1
    scheduler.add_job(sync_branch_logic, 'interval', seconds=5, args=["mysql", "第一分院", 1])
    
    # PG 是第二分院，只负责 Warehouse ID = 2
    scheduler.add_job(sync_branch_logic, 'interval', seconds=5, args=["pg", "第二分院", 2])
    
    scheduler.start()
    print("🚀 全量同步引擎已启动 (策略：权限分离 + 中央汇聚)...")