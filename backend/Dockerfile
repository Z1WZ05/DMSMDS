# 保持使用之前成功的镜像源
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 替换国内 APT 源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 【核心修改点 1】
# 将 backend 文件夹的内容拷贝到容器内的 /app/backend 目录下
# 这样 main.py 就依然位于一个名为 backend 的包里
COPY . ./backend

# 设置环境变量
ENV IS_DOCKER=true
ENV PYTHONPATH=/app

# 【核心修改点 2】
# 使用 -m 方式启动，确保相对导入 (.routers) 被正确解析
CMD ["python", "-m", "backend.main"]