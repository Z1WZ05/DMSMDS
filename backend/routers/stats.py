# backend/routers/stats.py 完整代码
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text, cast, Date
from ..database import SessionLocals
from ..security import get_current_user
from .. import models

router = APIRouter(prefix="/stats", tags=["统计分析"])

@router.get("/dashboard")
def get_dashboard_stats(start_date: str, end_date: str, current_user: dict = Depends(get_current_user)):
    db = SessionLocals[current_user['db_name']]()
    try:
        # 定义基础时间过滤器
        filters = [
            cast(models.Prescription.create_time, Date) >= start_date, 
            cast(models.Prescription.create_time, Date) <= end_date
        ]
        
        # === 核心权限逻辑修正 ===
        user_role = current_user['role']
        if user_role == 'super_admin':
            # 总院管理员：上帝视角，看全部数据，不加额外过滤
            pass 
        elif user_role == 'branch_admin':
            # 分院管理员：看本院全量数据
            filters.append(models.Prescription.warehouse_id == current_user['branch_id'])
        else:
            # 普通医护：只能看自己开出的数据
            filters.append(models.Prescription.doctor_id == current_user['id'])

        # 1. 汇总指标
        summary_data = db.query(
            func.count(models.Prescription.id),
            func.sum(models.Prescription.total_amount)
        ).filter(*filters).first()

        # 2. 院区营收对比 (条状图数据)
        # 即使是普通用户，我们也让他看到三个院区的对比图(满足你说的显示三个医院)，但汇总值仅基于他权限可见的部分
        branch_sales = db.query(
            models.Warehouse.name,
            func.sum(models.Prescription.total_amount)
        ).join(models.Prescription, models.Warehouse.id == models.Prescription.warehouse_id)\
         .filter(*filters).group_by(models.Warehouse.name).all()

        # 3. 药品单品排行与占比 (饼图 & 列表)
        med_stats = db.query(
            models.Medicine.name,
            func.sum(models.PrescriptionItem.quantity).label("total_qty"),
            func.sum(models.PrescriptionItem.quantity * models.PrescriptionItem.price_snapshot).label("total_money")
        ).join(models.PrescriptionItem).join(models.Prescription)\
         .filter(*filters).group_by(models.Medicine.name).all()

        # 4. 趋势图
        line_results = db.query(
            cast(models.Prescription.create_time, Date).label("d"),
            func.sum(models.Prescription.total_amount)
        ).filter(*filters).group_by(cast(models.Prescription.create_time, Date)).order_by("d").all()

        return {
            "summary": {"count": summary_data[0] or 0, "money": float(summary_data[1] or 0)},
            "branch_sales": [{"name": r[0], "value": float(r[1])} for r in branch_sales],
            "pie": [{"name": r.name, "value": float(r.total_money)} for r in med_stats],
            "line": {"dates": [str(r.d) for r in line_results], "values": [float(r[1]) for r in line_results]},
            "table": [{"medicine": r.name, "qty": int(r.total_qty), "money": float(r.total_money)} for r in med_stats]
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally: db.close()

@router.get("/sync-report")
def get_sync_report(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'super_admin': raise HTTPException(403)
    db = SessionLocals["mssql"]()
    try:
        # 获取最近 7 天的同步数据
        stats = db.query(models.SyncStats).order_by(models.SyncStats.sync_date.desc()).limit(7).all()
        # 反转数组，让时间顺序从左到右
        stats.reverse()
        return stats
    finally:
        db.close()