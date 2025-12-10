# backend/routers/analysis.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/analysis", tags=["复杂查询与分析"])

@router.get("/inventory-value", response_model=list[schemas.AnalysisResult])
def get_inventory_value_by_category(
    category: str, 
    db: Session = Depends(lambda: next(get_db("mssql"))) # 默认去 SQL Server (总库) 查
):
    """
    【满足任务书第5条】：多表连接、聚合查询
    功能：查询指定类别药品的总库存价值，并按仓库分组。
    SQL逻辑：
        SELECT w.name, SUM(m.price * i.quantity), m.category
        FROM inventory i
        JOIN medicines m ON i.medicine_id = m.id
        JOIN warehouses w ON i.warehouse_id = w.id
        WHERE m.category = :category
        GROUP BY w.name
    """
    results = (
        db.query(
            models.Warehouse.name.label("warehouse_name"),
            func.sum(models.Medicine.price * models.Inventory.quantity).label("total_value"),
            models.Medicine.category
        )
        .join(models.Inventory, models.Warehouse.id == models.Inventory.warehouse_id)
        .join(models.Medicine, models.Inventory.medicine_id == models.Medicine.id)
        .filter(models.Medicine.category == category)
        .group_by(models.Warehouse.name, models.Medicine.category)
        .all()
    )
    
    return results

# 数据库优化说明（写在实验报告里）：
# 为了优化上述查询，我们需要在 medicines 表的 category 字段上建立索引。
# CREATE INDEX idx_medicine_category ON medicines(category);