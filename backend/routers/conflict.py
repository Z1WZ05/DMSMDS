from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from pydantic import BaseModel
from datetime import datetime
from ..database import SessionLocals
from .. import models

router = APIRouter(prefix="/conflicts", tags=["冲突管理"])

class ConflictResolveRequest(BaseModel):
    log_id: int
    choice: str 

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

def copy_model_data(src_obj, target_obj, model_class):
    """辅助函数：将 src 的所有数据字段复制到 target"""
    mapper = inspect(model_class)
    for column in mapper.attrs:
        prop_name = column.key
        if prop_name == 'id': continue # ID 不复制
        
        # 复制值
        new_val = getattr(src_obj, prop_name)
        setattr(target_obj, prop_name, new_val)

@router.post("/resolve")
def resolve_conflict(req: ConflictResolveRequest):
    central_db = SessionLocals["mssql"]()
    try:
        # 1. 找到日志
        log = central_db.query(models.SyncConflictLog).filter(models.SyncConflictLog.id == req.log_id).first()
        if not log: raise HTTPException(404, "Log not found")
        if log.status == 'RESOLVED': return {"message": "已处理"}

        # 2. 建立两端连接
        source_session = SessionLocals[log.source_db]()
        target_session = SessionLocals[log.target_db]()

        try:
            # 3. 确定模型类 (目前只有 inventory 和 users)
            if log.table_name == 'inventory':
                ModelClass = models.Inventory
            elif log.table_name == 'users':
                ModelClass = models.User
            else:
                raise HTTPException(400, f"Unknown table: {log.table_name}")

            # 4. 锁定数据
            source_data = source_session.query(ModelClass).filter(ModelClass.id == log.record_id).first()
            target_data = target_session.query(ModelClass).filter(ModelClass.id == log.record_id).first()

            if not source_data or not target_data:
                raise HTTPException(404, "Data missing in DB")

            # 5. 【核心修复】执行覆盖并统一时间戳
            now_time = datetime.now() # 获取当前统一时间（北京时间）

            if req.choice == 'source':
                # 选择【以分院为准】：把 Source 的数据 强行覆盖给 Target
                copy_model_data(source_data, target_data, ModelClass)
                
                # 强制刷新两边的时间戳，确保它们一致且最新
                source_data.last_updated = now_time
                target_data.last_updated = now_time
                
                msg = f"已强制将 {log.target_db} 覆盖为 {log.source_db} 的数据"
            
            elif req.choice == 'target':
                # 选择【以总院为准】：把 Target 的数据 强行覆盖给 Source
                copy_model_data(target_data, source_data, ModelClass)
                
                # 强制刷新两边的时间戳
                source_data.last_updated = now_time
                target_data.last_updated = now_time
                
                msg = f"已强制将 {log.source_db} 覆盖为 {log.target_db} 的数据"
            
            else:
                raise HTTPException(400, "Invalid choice")

            # 6. 提交事务
            source_session.commit()
            target_session.commit()

            # 7. 标记日志已解决
            log.status = 'RESOLVED'
            log.resolved_time = now_time
            central_db.commit()

            return {"status": "success", "message": msg}

        except Exception as e:
            source_session.rollback()
            target_session.rollback()
            raise HTTPException(500, str(e))
        finally:
            source_session.close()
            target_session.close()
    finally:
        central_db.close()