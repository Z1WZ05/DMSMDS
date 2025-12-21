# backend/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Query

# 密钥 (真实项目中要保密，这里随便写)
SECRET_KEY = "SECRET_KEY_FOR_DMSMDS_PROJECT"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# OAuth2 方案 (Token 获取地址)
# 【核心修正】：增加 auto_error=False。
# 这样当请求头里没有 Authorization 时，FastAPI 不会立刻抛出 401，而是允许我们继续检查 URL 里的 ?token= 参数
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def create_access_token(data: dict):
    """生成 JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    """
    验证密码
    逻辑：
    1. 如果数据库里存的是哈希值 (以 $ 开头)，交给 passlib 库去验证。
    2. 如果数据库里存的是明文 (不以 $ 开头)，直接字符串比对。
    """
    if hashed_password.startswith("$"):
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
            
    # 兼容手动在数据库里改的明文密码 (如 "123")
    return plain_password == hashed_password

def get_password_hash(password):
    return pwd_context.hash(password)

# backend/security.py 中的 get_current_user 函数

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    token_query: Optional[str] = Query(None, alias="token") # 允许从 ?token=... 读取
):
    """依赖注入：从 Token 中解析出当前用户信息"""
    
    # 逻辑：优先取 Header 中的 token，如果没有（比如点击下载链接时），则取 URL 参数中的 token
    final_token = token or token_query
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 如果两个地方都没有 Token，手动抛出异常
    if not final_token:
        raise credentials_exception

    try:
        payload = jwt.decode(final_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        branch_id: int = payload.get("branch_id")
        user_id: int = payload.get("user_id")
        db_name: str = payload.get("db_name") 
        
        if username is None:
            raise credentials_exception
        
        return {
            "username": username, 
            "role": role, 
            "branch_id": branch_id, 
            "id": user_id,
            "db_name": db_name
        }
    except JWTError:
        raise credentials_exception