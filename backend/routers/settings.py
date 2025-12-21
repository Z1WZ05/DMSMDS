# backend/routers/settings.py 完整代码
from fastapi import APIRouter, Depends, HTTPException
from ..config import settings
from ..database import SessionLocals
from .. import models
from ..security import get_current_user
from ..sync_engine import scheduler
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["系统配置"])

class ConfigUpdate(BaseModel):
    real_time: bool
    scheduled: bool
    interval: int
    admin_email: str
    smtp_password: str
    frontend_url: str  # 【新增】支持修改前端 URL

@router.get("/")
def get_settings(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin': raise HTTPException(403)
    # 每次获取前先刷新一下内存
    settings.refresh()
    return {
        "real_time": settings.REAL_TIME_SYNC,
        "scheduled": settings.SCHEDULED_SYNC,
        "interval": settings.SYNC_INTERVAL,
        "admin_email": settings.SENDER_EMAIL,
        "smtp_password": settings.SMTP_PASSWORD,
        "frontend_url": settings.FRONTEND_URL # 【新增】返回当前 URL
    }

@router.put("/")
def update_settings(configs: ConfigUpdate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin': raise HTTPException(403)
    
    db = SessionLocals["mssql"]()
    try:
        cfg = db.query(models.SystemSetting).filter(models.SystemSetting.id == 1).first()
        if not cfg:
            cfg = models.SystemSetting(id=1)
            db.add(cfg)
        
        # 1. 更新数据库
        cfg.real_time_sync = int(configs.real_time)
        cfg.scheduled_sync = int(configs.scheduled)
        cfg.sync_interval = configs.interval
        cfg.sender_email = configs.admin_email
        cfg.smtp_password = configs.smtp_password
        cfg.frontend_url = configs.frontend_url # 【新增】保存到数据库
        db.commit()

        # 2. 同步更新内存
        old_interval = settings.SYNC_INTERVAL
        settings.refresh()

        # 3. 动态调整定时器周期
        if old_interval != configs.interval:
            scheduler.reschedule_job('sync_job_id', trigger='interval', seconds=settings.SYNC_INTERVAL)
            
        return {"message": "配置已成功保存至数据库并应用"}
    finally:
        db.close()