from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db, SessionLocals
from .. import models, security
from ..security import get_current_user

router = APIRouter(prefix="/users", tags=["用户管理"])

# Schema
class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    branch_id: int

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    branch_id: int
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    role: Optional[str] = None
    branch_id: Optional[int] = None

# 权限等级映射 (数字越大权限越高)
ROLE_LEVELS = {
    "nurse": 1,
    "doctor": 2,
    "emergency": 3,
    "branch_admin": 4,
    "super_admin": 5
}

# 1. 获取用户列表
@router.get("/", response_model=List[UserOut])
def get_users(current_user: dict = Depends(get_current_user)):
    user_role = current_user['role']
    user_branch = current_user['branch_id']
    db_name = current_user['db_name']
    
    db = SessionLocals[db_name]()
    try:
        query = db.query(models.User)
        
        # 逻辑：分院管理员只能看自己分院的用户
        if user_role == "branch_admin":
            query = query.filter(models.User.branch_id == user_branch)
        
        # 超级管理员可以看所有 (因为是全量同步，本地就有所有数据，直接查即可)
        elif user_role == "super_admin":
            pass # 查全部
        
        else:
            raise HTTPException(status_code=403, detail="无权查看用户列表")
            
        return query.all()
    finally:
        db.close()

# 2. 创建用户
@router.post("/")
def create_user(user: UserCreate, current_user: dict = Depends(get_current_user)):
    operator_role = current_user['role']
    operator_branch = current_user['branch_id']
    operator_level = ROLE_LEVELS.get(operator_role, 0)
    target_level = ROLE_LEVELS.get(user.role, 0)
    
    # 权限检查 1: 只能在自己分院创建 (超管除外)
    if operator_role == "branch_admin" and user.branch_id != operator_branch:
        raise HTTPException(status_code=403, detail="无法在其他分院创建用户")
        
    # 权限检查 2: 不能创建比自己权限高或相等的用户 (防篡位)
    if target_level >= operator_level:
        raise HTTPException(status_code=403, detail="无法创建同级或更高级别的用户")

    db_name = current_user['db_name']
    db = SessionLocals[db_name]()
    
    try:
        # 检查用户名重复
        if db.query(models.User).filter(models.User.username == user.username).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
            
        new_user = models.User(
            username=user.username,
            password=security.get_password_hash(user.password), # 哈希加密
            role=user.role,
            branch_id=user.branch_id
        )
        db.add(new_user)
        db.commit()
        return {"status": "success", "message": "用户创建成功，等待同步..."}
    finally:
        db.close()

# 3. 修改用户 (权限调整)
@router.put("/{user_id}")
def update_user(user_id: int, update: UserUpdate, current_user: dict = Depends(get_current_user)):
    # 逻辑同创建：不能越权修改
    operator_level = ROLE_LEVELS.get(current_user['role'], 0)
    
    if update.role:
        target_level = ROLE_LEVELS.get(update.role, 0)
        if target_level >= operator_level:
            raise HTTPException(status_code=403, detail="无法赋予该权限等级")

    db_name = current_user['db_name']
    db = SessionLocals[db_name]()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(404, "User not found")
            
        # 分院管理员只能改自己院的人
        if current_user['role'] == "branch_admin" and user.branch_id != current_user['branch_id']:
             raise HTTPException(403, "无权修改其他分院用户")

        if update.role: user.role = update.role
        if update.branch_id: user.branch_id = update.branch_id
        
        db.commit()
        return {"status": "success"}
    finally:
        db.close()