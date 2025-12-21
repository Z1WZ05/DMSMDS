from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import inspect, text
from ..database import SessionLocals
from ..security import get_current_user
from .. import models
from datetime import datetime
from typing import List

router = APIRouter(prefix="/maintenance", tags=["系统维护与迁移"])

# 定义需要备份/迁移的表顺序（注意外键依赖：先删子表，后删父表；先插父表，后插子表）
TABLE_MODELS = [
    models.Medicine, 
    models.Warehouse, 
    models.User, 
    models.Inventory, 
    models.Prescription, 
    models.PrescriptionItem
]

# --- 1. 数据备份 (导出通用 SQL 脚本) ---
@router.get("/backup/{db_name}")
def export_database_backup(db_name: str, current_user: dict = Depends(get_current_user)):
    """
    【满足要求 3.f】生成数据库备份脚本。
    逻辑：遍历所有表，将每行记录转化为 INSERT INTO 语句。
    """
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="权限不足")
    
    if db_name not in SessionLocals:
        raise HTTPException(status_code=404, detail="未知数据库标识")

    db = SessionLocals[db_name]()
    sql_output = f"-- DMSMDS 系统自动备份\n-- 源数据库: {db_name}\n-- 导出时间: {datetime.now()}\n"
    sql_output += "SET FOREIGN_KEY_CHECKS = 0;\n\n" # 针对 MySQL 暂时关闭外键检查

    try:
        for model in TABLE_MODELS:
            table_name = model.__tablename__
            sql_output += f"-- ----------------------------\n-- Table structure for {table_name}\n-- ----------------------------\n"
            
            rows = db.query(model).all()
            if not rows:
                continue

            # 获取列名
            columns = [c.key for c in inspect(model).attrs if not c.key.startswith('_')]
            
            for row in rows:
                vals = []
                for col in columns:
                    v = getattr(row, col)
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    else:
                        # 处理字符串中的单引号，防止 SQL 注入或中断
                        safe_val = str(v).replace("'", "''")
                        vals.append(f"'{safe_val}'")
                
                sql_output += f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(vals)});\n"
            sql_output += "\n"
        
        filename = f"backup_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        return PlainTextResponse(
            sql_output, 
            media_type="application/sql",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        db.close()

# --- 2. 整库迁移 (一键克隆) ---
@router.post("/migrate")
def migrate_database(source_db: str, target_db: str, current_user: dict = Depends(get_current_user)):
    """
    【满足要求 4.1】支持表迁移，整库迁移。
    逻辑：清空目标库 -> 从源库读取全量数据 -> 转换 ID 偏移 -> 写入目标库。
    """
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="权限不足")
    
    if source_db == target_db:
        raise HTTPException(status_code=400, detail="源数据库与目标数据库不能相同")

    s_db = SessionLocals[source_db]()
    t_db = SessionLocals[target_db]()

    try:
        # 1. 按照反向依赖顺序清空目标库
        for model in reversed(TABLE_MODELS):
            t_db.execute(text(f"DELETE FROM {model.__tablename__}"))
        
        # 2. 按照依赖顺序迁移数据
        for model in TABLE_MODELS:
            rows = s_db.query(model).all()
            for row in rows:
                # 提取数据
                new_data = {c.key: getattr(row, c.key) for c in inspect(model).attrs if not c.key.startswith('_')}
                
                # 【核心补丁】处理你之前的 PG ID 不对齐问题 (+253 逻辑)
                if 'medicine_id' in new_data and new_data['medicine_id'] is not None:
                    # 如果是从非 PG 迁往 PG
                    if source_db != 'pg' and target_db == 'pg':
                        new_data['medicine_id'] += 253
                    # 如果是从 PG 迁往 非 PG
                    elif source_db == 'pg' and target_db != 'pg':
                        new_data['medicine_id'] -= 253

                t_db.add(model(**new_data))
            
            t_db.flush() # 每迁移一张表刷新一次缓存
            
        t_db.commit()
        return {"status": "success", "message": f"整库迁移成功: {source_db} -> {target_db}"}
    except Exception as e:
        t_db.rollback()
        raise HTTPException(status_code=500, detail=f"迁移失败: {str(e)}")
    finally:
        s_db.close()
        t_db.close()