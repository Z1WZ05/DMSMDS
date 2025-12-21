# backend/config.py 完整代码

from .database import SessionLocals
from . import models

class SystemConfig:
    def __init__(self):
        # 默认值
        self.REAL_TIME_SYNC = True
        self.SCHEDULED_SYNC = True
        self.SYNC_INTERVAL = 90
        self.SMTP_SERVER = "smtp.qq.com"
        self.SMTP_PORT = 465
        self.SENDER_EMAIL = ""
        self.SMTP_PASSWORD = ""
        self.FRONTEND_URL = "http://127.0.0.1:5173"

    def refresh(self):
        """从总库 (MSSQL) 加载最新设置，仅在发生变化时更新并打印日志"""
        db = SessionLocals["mssql"]()
        try:
            cfg = db.query(models.SystemSetting).filter(models.SystemSetting.id == 1).first()
            if cfg:
                # 【核心逻辑】比对是否有变化
                has_changed = (
                    self.REAL_TIME_SYNC != bool(cfg.real_time_sync) or
                    self.SCHEDULED_SYNC != bool(cfg.scheduled_sync) or
                    self.SYNC_INTERVAL != cfg.sync_interval or
                    self.SENDER_EMAIL != (cfg.sender_email or "") or
                    self.SMTP_PASSWORD != (cfg.smtp_password or "") or
                    self.FRONTEND_URL != (cfg.frontend_url or "")
                )

                if has_changed:
                    # 只有变化了才赋值并打印
                    self.REAL_TIME_SYNC = bool(cfg.real_time_sync)
                    self.SCHEDULED_SYNC = bool(cfg.scheduled_sync)
                    self.SYNC_INTERVAL = cfg.sync_interval
                    self.SENDER_EMAIL = cfg.sender_email or ""
                    self.SMTP_PASSWORD = cfg.smtp_password or ""
                    self.FRONTEND_URL = cfg.frontend_url or ""
                    
                    print(f"⚙️ [系统设置已更新] Email: {self.SENDER_EMAIL}, 周期: {self.SYNC_INTERVAL}s")
            
        except Exception as e:
            # 这里的打印保留，因为报错是异常情况，需要看到
            print(f"❌ 刷新设置失败: {e}")
        finally:
            db.close()

# 全局单例
settings = SystemConfig()