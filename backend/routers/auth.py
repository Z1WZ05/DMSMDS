from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocals
from .. import models, security

router = APIRouter(prefix="/auth", tags=["认证与登录"])

# 分院ID 到 数据库名 的映射
BRANCH_DB_MAP = {
    1: "mysql",   # 分院1 -> MySQL
    2: "pg",      # 分院2 -> PostgreSQL
    3: "mssql"    # 总院 -> SQL Server
}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    
    user = None
    
    # 1. 轮询所有数据库查找用户 (利用数据冗余提高可用性)
    for db_scan in ["mysql", "pg", "mssql"]:
        db = SessionLocals[db_scan]()
        try:
            found_user = db.query(models.User).filter(models.User.username == username).first()
            if found_user:
                # 验证密码
                if security.verify_password(password, found_user.password):
                    user = found_user
                    break # 密码验证通过，跳出循环
        except Exception:
            continue
        finally:
            db.close()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 智能路由：根据 branch_id 决定该用户应该去连哪个库
    target_db_name = BRANCH_DB_MAP.get(user.branch_id)
    
    if not target_db_name:
        raise HTTPException(status_code=500, detail=f"配置错误：未知的分院ID {user.branch_id}")

    # 3. 生成 Token
    access_token = security.create_access_token(
        data={
            "sub": user.username, 
            "role": user.role, 
            "branch_id": user.branch_id,
            "user_id": user.id,
            "db_name": target_db_name # 前端后续请求都会发往这个库
        }
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user.role, 
        "db_name": target_db_name,
        "username": user.username
    }