import time
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import inspect, and_
from datetime import datetime, timedelta
from .database import SessionLocals
from . import models
from .config import settings
from .utils import send_conflict_email

scheduler = BackgroundScheduler()

# 定义所有数据库节点
ALL_DBS = ["mysql", "pg", "mssql"]

# 数据归属映射 (ID -> 负责的 DB Name)
OWNER_MAP = {1: "mysql", 2: "pg", 3: "mssql"}

# 时钟偏差容忍阈值 (秒)
CLOCK_SKEW_TOLERANCE = 10 

def get_db_session(db_name):
    return SessionLocals[db_name]()

def update_daily_stats(stat_type: str):
    """
    【统计逻辑】更新每日统计指标：'auto' (自动同步), 'conflict' (冲突), 'resolve' (手动解决)
    """
    db = SessionLocals["mssql"]() # 统计统一存在总库
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        stat = db.query(models.SyncStats).filter(models.SyncStats.sync_date == today).first()
        if not stat:
            stat = models.SyncStats(sync_date=today, auto_sync_count=0, conflict_count=0, manual_resolve_count=0)
            db.add(stat)
        
        if stat_type == 'auto': 
            stat.auto_sync_count += 1
        elif stat_type == 'conflict': 
            stat.conflict_count += 1
        elif stat_type == 'resolve': 
            stat.manual_resolve_count += 1
        
        db.commit()
    except Exception as e:
        print(f"统计更新失败: {e}")
    finally:
        db.close()

def is_record_locked(table_name, record_id):
    """检查记录是否处于冲突锁定状态"""
    db = SessionLocals["mssql"]()
    try:
        conflict = db.query(models.SyncConflictLog).filter(
            and_(
                models.SyncConflictLog.table_name == table_name,
                models.SyncConflictLog.record_id == str(record_id),
                models.SyncConflictLog.status == 'PENDING'
            )
        ).first()
        return conflict is not None
    finally:
        db.close()

def log_conflict(table, record_id, owner_db, intruder_db, diff_msg):
    """记录冲突并触发邮件报警"""
    db = SessionLocals["mssql"]()
    try:
        exists = db.query(models.SyncConflictLog).filter(
            and_(
                models.SyncConflictLog.table_name == table,
                models.SyncConflictLog.record_id == str(record_id),
                models.SyncConflictLog.status == 'PENDING'
            )
        ).first()
        
        if not exists:
            detailed_reason = f"内容冲突: {diff_msg}"
            print(f"📧 [冲突报警] {table}:{record_id} -> {detailed_reason}")
            
            # 1. 存入冲突表
            conflict = models.SyncConflictLog(
                table_name=table,
                record_id=str(record_id),
                source_db=owner_db,
                target_db=intruder_db,
                conflict_reason=detailed_reason,
                status='PENDING'
            )
            db.add(conflict)
            db.commit()
            
            # 2. 增加冲突统计计数
            update_daily_stats('conflict')
            
            # 3. 触发邮件通知
            try:
                send_conflict_email(table, record_id, detailed_reason)
            except Exception as mail_err:
                print(f"邮件发送失败: {mail_err}")
    finally:
        db.close()

def get_model_diff_str(obj1, obj2, model_class, source_db, target_db):
    """【内容比对】加入 PostgreSQL ID 偏移兼容 (+253)"""
    mapper = inspect(model_class)
    diffs = []
    for column in mapper.attrs:
        prop_name = column.key
        if prop_name in ['last_updated', 'create_time'] or prop_name.startswith('_'): 
            continue
        
        v1 = getattr(obj1, prop_name)
        v2 = getattr(obj2, prop_name)

        # 处理 medicine_id 偏移补偿比对
        if prop_name == 'medicine_id':
            if source_db != 'pg' and target_db == 'pg':
                if v1 is not None: v1 += 253
            elif source_db == 'pg' and target_db != 'pg':
                if v1 is not None: v1 -= 253

        is_different = False
        if isinstance(v1, float) and isinstance(v2, float):
            if abs(v1 - v2) > 0.001: is_different = True
        elif v1 != v2:
            is_different = True
        
        if is_different:
            diffs.append(f"{prop_name}:[{v1} vs {v2}]")
            
    return ", ".join(diffs) if diffs else None

def get_owner_db(item, source_db_name):
    """判断数据拥有者"""
    owner_id = getattr(item, 'branch_id', getattr(item, 'warehouse_id', -1))
    if hasattr(item, 'prescription_id'):
        if source_db_name == 'mysql': owner_id = 1
        elif source_db_name == 'pg': owner_id = 2
        else: owner_id = 3
    return OWNER_MAP.get(owner_id)

def sync_logic():
    """全能网格广播同步引擎：支持全表监控、冲突锁定、ID偏移补丁、精准统计"""
    sync_models = [models.User, models.Inventory, models.Prescription, models.PrescriptionItem, models.AlertMessage]

    for model_class in sync_models:
        table_name = model_class.__tablename__
        for source_db_name in ALL_DBS:
            source_session = get_db_session(source_db_name)
            try:
                items = source_session.query(model_class).all()
                for item in items:
                    if is_record_locked(table_name, item.id): continue

                    owner_db = get_owner_db(item, source_db_name)
                    if owner_db != source_db_name: continue 

                    for target_db_name in ALL_DBS:
                        if target_db_name == source_db_name: continue
                        target_session = get_db_session(target_db_name)
                        try:
                            target_item = target_session.query(model_class).filter(model_class.id == item.id).first()
                            
                            if not target_item:
                                # [新增同步]
                                new_data = {c.key: getattr(item, c.key) for c in inspect(model_class).attrs if c.key != 'id'}
                                if target_db_name == 'pg' and 'medicine_id' in new_data:
                                    new_data['medicine_id'] += 253
                                target_session.add(model_class(id=item.id, **new_data))
                                target_session.commit()
                                # 时间戳对齐
                                t_ref = target_session.query(model_class).filter(model_class.id == item.id).first()
                                if t_ref:
                                    t_ref.last_updated = item.last_updated
                                    target_session.commit()
                                
                                # 【核心修改】执行了真实的插入，统计数+1
                                update_daily_stats('auto') 
                                print(f"➕ [同步新增] {table_name}:{str(item.id)[:8]} {source_db_name}->{target_db_name}")

                            else:
                                diff_str = get_model_diff_str(item, target_item, model_class, source_db_name, target_db_name)
                                
                                # 情况 2: Owner 时间领先 (正常更新)
                                if item.last_updated > target_item.last_updated:
                                    if diff_str:
                                        # 内容有变，执行更新
                                        for c in inspect(model_class).attrs:
                                            if c.key != 'id': 
                                                val = getattr(item, c.key)
                                                if target_db_name == 'pg' and c.key == 'medicine_id': val += 253
                                                setattr(target_item, c.key, val)
                                        target_session.commit()
                                        
                                        # 【核心修改】内容变了才计入统计，并打印日志
                                        update_daily_stats('auto')
                                        print(f"⬆️ [同步更新] {table_name}:{str(item.id)[:8]} {source_db_name}->{target_db_name} | {diff_str}")
                                    else:
                                        # 仅时间偏移，静默对齐，不计入同步次数，不打印日志
                                        target_item.last_updated = item.last_updated
                                        target_session.commit()
                                
                                # 情况 3: Target 时间领先 (潜在冲突)
                                elif target_item.last_updated > item.last_updated:
                                    if diff_str:
                                        delta = (target_item.last_updated - item.last_updated).total_seconds()
                                        if delta < CLOCK_SKEW_TOLERANCE:
                                            # 时钟纠偏
                                            for c in inspect(model_class).attrs:
                                                if c.key != 'id':
                                                    val = getattr(item, c.key)
                                                    if target_db_name == 'pg' and c.key == 'medicine_id': val += 253
                                                    setattr(target_item, c.key, val)
                                            target_item.last_updated = item.last_updated
                                            target_session.commit()
                                        else:
                                            # 确认为非拥有者篡改 -> 报警
                                            log_conflict(table_name, item.id, source_db_name, target_db_name, diff_str)
                        except Exception:
                            target_session.rollback()
                        finally:
                            target_session.close()
            finally:
                source_session.close()

def scheduled_task():
    """定时任务：自动刷新配置并执行同步"""
    settings.refresh()
    if settings.SCHEDULED_SYNC: 
        sync_logic()

def start_sync_job():
    # 使用动态参数启动
    scheduler.add_job(scheduled_task, 'interval', seconds=settings.SYNC_INTERVAL, id='sync_job_id', max_instances=3, coalesce=True)
    scheduler.start()