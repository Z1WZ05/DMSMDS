# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 【关键缺失】
from contextlib import asynccontextmanager
from .routers import analysis, medicine, conflict, auth, business
from .sync_engine import start_sync_job, scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动同步引擎
    start_sync_job()
    yield
    scheduler.shutdown()

app = FastAPI(
    title="DMSMDS Backend",
    version="1.0.0",
    lifespan=lifespan
)

# 【核心修复】配置 CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应指定 http://localhost:5173）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法 (GET, POST...)
    allow_headers=["*"],  # 允许所有 Header
)

# 注册路由
app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(medicine.router)
app.include_router(conflict.router)
app.include_router(business.router)

@app.get("/")
def root():
    return {"message": "System is Online", "docs_url": "http://127.0.0.1:8000/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)