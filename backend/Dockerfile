# ============================================================
# NovaMind Backend Dockerfile
# Python 3.12 + FastAPI + uvicorn
# 使用阿里云镜像加速（适配中国服务器）
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（PyMuPDF 需要 libmupdf）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .

# 使用阿里云 PyPI 镜像加速（中国服务器必备）
RUN pip install --no-cache-dir \
    --timeout 120 \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 8000

# 启动脚本（先等待 DB，再启动服务）
COPY start.sh /start.sh
# 修复 Windows CRLF 换行符，确保脚本在 Linux 容器中可执行
RUN sed -i 's/\r$//' /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
