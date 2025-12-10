# backend/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import analysis, medicine
from .sync_engine import start_sync_job, scheduler # 导入同步引擎

# 定义生命周期：服务器启动时做什么，关闭时做什么
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 启动时：开启同步任务
    start_sync_job()
    yield
    # 2. 关闭时：关闭调度器
    scheduler.shutdown()

app = FastAPI(
    title="DMSMDS Backend",
    description="分布式医疗物资调度系统后端 API",
    version="1.0.0",
    lifespan=lifespan # 挂载生命周期
)

app.include_router(analysis.router)
app.include_router(medicine.router)

@app.get("/")
def root():
    return {"message": "System is Online", "docs_url": "http://127.0.0.1:8000/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)