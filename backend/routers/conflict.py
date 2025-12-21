from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..database import SessionLocals
from .. import models
from ..sync_engine import update_daily_stats # 引入

router = APIRouter(prefix="/conflicts", tags=["冲突管理"])

# --- 数据验证 Schema ---

class ConflictResolveRequest(BaseModel):
    log_id: int
    db_choice: str  # 管理员选定的权威数据库：'mysql', 'pg', 或 'mssql'

class ConflictLogOut(BaseModel):
    id: int
    conflict_reason: str
    create_time: datetime
    table_name: str
    source_db: str
    target_db: str
    record_id: str  # 兼容 UUID 字符串和 整数 ID
    status: str
    resolution_choice: Optional[str] = None  # 处理结果
    resolved_time: Optional[datetime] = None # 处理时间
    class Config:
        from_attributes = True

# --- 内部辅助工具 ---

def get_model_class(table_name: str):
    """
    根据数据库表名，动态映射到后端对应的 SQLAlchemy 模型类
    【修正】：增加了对 alert_messages 表的支持
    """
    table_map = {
        'users': models.User,
        'inventory': models.Inventory,
        'prescriptions': models.Prescription,
        'prescription_items': models.PrescriptionItem,
        'alert_messages': models.AlertMessage  # 确保预警信息的冲突也能处理
    }
    return table_map.get(table_name)

def extract_normalized_data(src_obj, model_class, src_db_name):
    """
    【核心补丁】：从源对象提取数据并归一化
    逻辑：如果是从 PG 提取，medicine_id 需要减去 253 变成标准 ID 1, 2, 3...
    这样在分发给其他库时才不会出错。
    """
    mapper = inspect(model_class)
    data = {}
    for column in mapper.attrs:
        prop_name = column.key
        # 排除主键和系统自动生成的字段
        if prop_name in ['id', 'last_updated', 'create_time', '_sa_instance_state']:
            continue
        
        val = getattr(src_obj, prop_name)
        
        # ID 归一化：处理分院2 (PostgreSQL) 的特殊偏移
        if prop_name == 'medicine_id' and src_db_name == 'pg' and val is not None:
            val -= 253
            
        data[prop_name] = val
    return data

def apply_data_with_offset(target_obj, data_dict, target_db_name):
    """
    【核心补丁】：将归一化后的数据写入目标对象
    逻辑：如果目标是 PG，medicine_id 需要重新加上 253。
    """
    for key, val in data_dict.items():
        # ID 差异化写入
        if key == 'medicine_id' and target_db_name == 'pg' and val is not None:
            setattr(target_obj, key, val + 253)
        else:
            setattr(target_obj, key, val)

# --- API 接口实现 ---

@router.get("/", response_model=List[ConflictLogOut])
def get_pending_conflicts():
    """获取所有待处理的冲突列表（从总库读取）"""
    db = SessionLocals["mssql"]() 
    try:
        conflicts = db.query(models.SyncConflictLog).filter(
            models.SyncConflictLog.status == 'PENDING'
        ).order_by(models.SyncConflictLog.create_time.desc()).all()
        return conflicts
    finally:
        db.close()

@router.get("/history", response_model=List[ConflictLogOut])
def get_conflict_history():
    """获取所有已解决的冲突历史记录"""
    db = SessionLocals["mssql"]()
    try:
        history = db.query(models.SyncConflictLog).filter(
            models.SyncConflictLog.status == 'RESOLVED'
        ).order_by(models.SyncConflictLog.resolved_time.desc()).all()
        return history
    finally:
        db.close()

@router.post("/resolve")
def resolve_conflict(req: ConflictResolveRequest):
    """
    【核心仲裁逻辑 - 完整版】
    1. 选定一个库作为“真理”。
    2. 自动处理跨库 ID 偏移 (+253)。
    3. 同时强制更新全网三个数据库，确保数据绝对同步。
    4. 对齐所有库的时间戳，解除同步引擎的死循环报警。
    """
    central_db = SessionLocals["mssql"]()
    try:
        # A. 查找冲突日志
        log = central_db.query(models.SyncConflictLog).filter(models.SyncConflictLog.id == req.log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="找不到该冲突记录")
        if log.status == 'RESOLVED':
            return {"message": "该冲突此前已被处理"}

        # B. 获取对应的数据库模型类
        ModelClass = get_model_class(log.table_name)
        if not ModelClass:
            raise HTTPException(status_code=400, detail=f"暂不支持处理表 {log.table_name} 的冲突")

        # C. 准备连接全网三个数据库
        sessions = {
            "mysql": SessionLocals["mysql"](),
            "pg": SessionLocals["pg"](),
            "mssql": SessionLocals["mssql"]()
        }

        try:
            # D. 提取并“洗白”选中的权威数据
            chosen_session = sessions.get(req.db_choice)
            master_record = chosen_session.query(ModelClass).filter(ModelClass.id == log.record_id).first()
            
            if not master_record:
                raise HTTPException(status_code=400, detail=f"选定的数据库 {req.db_choice} 中该记录已失踪")

            # 将选中数据提取为通用的 dict（自动处理 -253 逻辑）
            normalized_data = extract_normalized_data(master_record, ModelClass, req.db_choice)

            # E. 执行全网强制同步覆盖
            now_time = datetime.now()

            for db_name, sess in sessions.items():
                target_record = sess.query(ModelClass).filter(ModelClass.id == log.record_id).first()
                
                if target_record:
                    # 场景 1：目标库已有记录 -> 执行更新并处理偏移
                    apply_data_with_offset(target_record, normalized_data, db_name)
                    target_record.last_updated = now_time
                else:
                    # 场景 2：目标库缺失记录 -> 执行强制创建
                    new_params = {}
                    for k, v in normalized_data.items():
                        if k == 'medicine_id' and db_name == 'pg':
                            new_params[k] = v + 253
                        else:
                            new_params[k] = v
                    
                    new_obj = ModelClass(id=master_record.id, **new_params)
                    new_obj.last_updated = now_time
                    sess.add(new_obj)
                
                # 提交当前数据库的事务
                sess.commit()

            # F. 结案并记录审计
            log.status = 'RESOLVED'
            log.resolution_choice = req.db_choice
            log.resolved_time = now_time
            central_db.commit()

            update_daily_stats('resolve') # 【新增】

            return {
                "status": "success", 
                "message": f"仲裁成功！已将全网数据同步为 {req.db_choice} 的权威版本。"
            }

        except Exception as inner_e:
            # 异常时回滚所有库，防止数据不一致
            for s in sessions.values(): s.rollback()
            print(f"❌ 跨库同步执行失败: {inner_e}")
            raise HTTPException(status_code=500, detail=f"执行失败: {str(inner_e)}")
        finally:
            # 释放所有数据库连接
            for s in sessions.values(): s.close()

    finally:
        central_db.close()