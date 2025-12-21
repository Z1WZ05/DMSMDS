from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db, SessionLocals
from .. import models, security
from ..security import get_current_user

router = APIRouter(prefix="/users", tags=["用户管理"])

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

ROLE_LEVELS = { "nurse": 1, "doctor": 2, "emergency": 3, "branch_admin": 4, "super_admin": 5 }

@router.get("/", response_model=List[UserOut])
def get_users(current_user: dict = Depends(get_current_user)):
    user_role = current_user['role']
    user_branch = current_user['branch_id']
    db_name = current_user['db_name']
    
    db = SessionLocals[db_name]()
    try:
        query = db.query(models.User)
        if user_role == "branch_admin":
            query = query.filter(models.User.branch_id == user_branch)
        elif user_role == "super_admin":
            pass 
        else:
            raise HTTPException(status_code=403, detail="无权查看")
        return query.all()
    finally:
        db.close()

@router.post("/")
def create_user(user: UserCreate, current_user: dict = Depends(get_current_user)):
    # ... (保持之前的创建逻辑不变，略) ...
    # 为了完整性，建议你保留之前的 create_user 代码，这里我不重复占用篇幅
    # 如果需要完整代码，我可以再发一次
    operator_role = current_user['role']
    operator_branch = current_user['branch_id']
    operator_level = ROLE_LEVELS.get(operator_role, 0)
    target_level = ROLE_LEVELS.get(user.role, 0)
    
    if operator_role == "branch_admin" and user.branch_id != operator_branch:
        raise HTTPException(status_code=403, detail="无法在其他分院创建用户")
    if target_level >= operator_level:
        raise HTTPException(status_code=403, detail="无法创建同级或更高级别的用户")

    db_name = current_user['db_name']
    db = SessionLocals[db_name]()
    try:
        if db.query(models.User).filter(models.User.username == user.username).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
        new_user = models.User(
            username=user.username,
            password=security.get_password_hash(user.password),
            role=user.role,
            branch_id=user.branch_id
        )
        db.add(new_user)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

@router.put("/{user_id}")
def update_user(user_id: int, update: UserUpdate, current_user: dict = Depends(get_current_user)):
    # ... (保持之前的更新逻辑不变) ...
    operator_level = ROLE_LEVELS.get(current_user['role'], 0)
    if update.role:
        target_level = ROLE_LEVELS.get(update.role, 0)
        if target_level >= operator_level:
            raise HTTPException(403, "无法赋予该权限")

    db = SessionLocals[current_user['db_name']]()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user: raise HTTPException(404, "User not found")
        if current_user['role'] == "branch_admin" and user.branch_id != current_user['branch_id']:
             raise HTTPException(403, "无权修改其他分院用户")

        if update.role: user.role = update.role
        if update.branch_id: user.branch_id = update.branch_id
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

# 【新增】删除用户
@router.delete("/{user_id}")
def delete_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """
    删除用户接口
    """
    if user_id == current_user['id']:
        raise HTTPException(400, "不能删除自己")

    db = SessionLocals[current_user['db_name']]()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(404, "用户不存在")
        
        # 权限校验
        if current_user['role'] == "branch_admin":
            if user.branch_id != current_user['branch_id']:
                raise HTTPException(403, "无权删除其他分院用户")
            # 也可以加逻辑：不能删比自己级高的人（虽然创建时限制了，但为了安全）
            
        elif current_user['role'] != "super_admin":
            raise HTTPException(403, "权限不足")

        db.delete(user)
        db.commit()
        return {"status": "success", "message": "用户已删除"}
    finally:
        db.close()