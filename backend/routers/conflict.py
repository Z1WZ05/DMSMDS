# backend/routers/conflict.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from ..database import get_db, SessionLocals
from .. import models, schemas

router = APIRouter(prefix="/conflicts", tags=["冲突管理"])

# --- Schema 定义 ---
class ConflictResolveRequest(BaseModel):
    log_id: int      # 冲突日志的 ID
    choice: str      # 'source' (以分院为准) 或 'target' (以总院为准)

class ConflictLogOut(BaseModel):
    id: int
    conflict_reason: str
    create_time: datetime
    table_name: str
    source_db: str
    target_db: str
    record_id: int
    status: str
    class Config:
        from_attributes = True

# 1. 获取所有待处理的冲突列表
@router.get("/", response_model=list[ConflictLogOut])
def get_pending_conflicts(): 

    central_db = SessionLocals["mssql"]()
    try:
        conflicts = central_db.query(models.SyncConflictLog).filter(
            models.SyncConflictLog.status == 'PENDING'
        ).all()
        return conflicts
    finally:
        central_db.close()

# 2. 处理冲突 (核心接口)
@router.post("/resolve")
def resolve_conflict(req: ConflictResolveRequest):
    """
    管理员选择以哪个数据库为准，强制覆盖另一个。
    """
    central_db = SessionLocals["mssql"]()
    
    try:
        # 1. 找到冲突日志
        log = central_db.query(models.SyncConflictLog).filter(models.SyncConflictLog.id == req.log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        
        if log.status == 'RESOLVED':
            return {"message": "该冲突已被处理"}

        # 2. 获取两个数据库的连接
        # log.source_db 比如是 'mysql', log.target_db 是 'mssql'
        source_session = SessionLocals[log.source_db]()
        target_session = SessionLocals[log.target_db]()

        try:
            # 3. 读取两边的数据
            # 假设冲突发生在 inventory 表
            if log.table_name == 'inventory':
                ModelClass = models.Inventory
            else:
                raise HTTPException(status_code=400, detail="Unknown table")

            source_data = source_session.query(ModelClass).filter(ModelClass.id == log.record_id).first()
            target_data = target_session.query(ModelClass).filter(ModelClass.id == log.record_id).first()

            if not source_data or not target_data:
                raise HTTPException(status_code=404, detail="Data record missing in one of the DBs")

            # 4. 根据管理员的选择执行覆盖
            if req.choice == 'source':
                # 【选择：以分院为准】 -> 强制把分院数据写入总院
                target_data.quantity = source_data.quantity
                target_data.last_updated = datetime.now() # 更新时间戳，确保后续同步正常
                # 同时也要把分院的时间戳更新一下，防止下次同步又误判
                source_data.last_updated = datetime.now()
                msg = f"已强制将 {log.target_db} 数据覆盖为 {log.source_db} 的值 ({source_data.quantity})"
            
            elif req.choice == 'target':
                # 【选择：以总院为准】 -> 强制把总院数据写入分院
                source_data.quantity = target_data.quantity
                source_data.last_updated = datetime.now()
                target_data.last_updated = datetime.now()
                msg = f"已强制将 {log.source_db} 数据覆盖为 {log.target_db} 的值 ({target_data.quantity})"
            
            else:
                raise HTTPException(status_code=400, detail="Invalid choice")

            # 5. 提交事务
            source_session.commit()
            target_session.commit()

            # 6. 更新日志状态为已解决
            log.status = 'RESOLVED'
            log.resolved_time = datetime.now()
            central_db.commit()

            return {"status": "success", "message": msg}

        except Exception as inner_e:
            source_session.rollback()
            target_session.rollback()
            raise inner_e
        finally:
            source_session.close()
            target_session.close()

    finally:
        central_db.close()