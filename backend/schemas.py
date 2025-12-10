# backend/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- 药品相关 ---
class MedicineBase(BaseModel):
    name: str
    category: Optional[str] = None
    price: float
    danger_level: Optional[str] = None

class MedicineCreate(MedicineBase):
    pass

class Medicine(MedicineBase):
    id: int
    class Config:
        from_attributes = True # 允许从 ORM 模型读取数据

# --- 库存相关 ---
class InventoryBase(BaseModel):
    medicine_id: int
    warehouse_id: int
    quantity: int

class Inventory(InventoryBase):
    id: int
    last_updated: datetime
    class Config:
        from_attributes = True

# --- 复杂查询返回结果 ---
class AnalysisResult(BaseModel):
    warehouse_name: str
    total_value: float
    category: str