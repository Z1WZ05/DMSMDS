from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocals
from .. import models, security

router = APIRouter(prefix="/auth", tags=["认证与登录"])

# 【核心修复】定义数据库与分院ID的绑定关系
# 必须和 seed_data.py 里的定义一致
DB_BRANCH_MAP = {
    "mysql": 1,   # MySQL 对应 分院1
    "pg": 2,      # PG 对应 分院2
    "mssql": 3    # MSSQL 对应 总院
}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    
    user = None
    target_db_name = None
    
    # 轮询查找用户
    for db_name in ["mysql", "pg", "mssql"]:
        db = SessionLocals[db_name]()
        try:
            # 1. 查找用户
            found_user = db.query(models.User).filter(models.User.username == username).first()
            
            if found_user:
                # 2. 验证密码
                if found_user.password == password:
                    # 3. 【关键修复】验证归属权 (Authority Check)
                    # 只有当用户的 branch_id 与当前数据库的身份匹配时，才允许登录
                    # 或者是超级管理员(branch_id=3)，我们允许他在总院登录
                    
                    expected_branch_id = DB_BRANCH_MAP.get(db_name)
                    
                    if found_user.branch_id == expected_branch_id:
                        user = found_user
                        target_db_name = db_name
                        break # 找到了真正的本尊，停止轮询
                    else:
                        # 虽然在这个库找到了用户，但它的 branch_id 不对
                        # 说明这是同步过来的“副本账号”，不能用来登录
                        # 继续找下一个库...
                        pass
        except Exception as e:
            print(f"Login error in {db_name}: {e}")
        finally:
            db.close()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名密码错误，或未找到归属分院",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成 Token
    access_token = security.create_access_token(
        data={
            "sub": user.username, 
            "role": user.role, 
            "branch_id": user.branch_id,
            "user_id": user.id,
            "db_name": target_db_name 
        }
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user.role, 
        "db_name": target_db_name,
        "username": user.username
    }