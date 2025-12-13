# 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 定义构建时参数（ARG - 仅在构建时可用）
ARG PYTHON_VERSION=3.11
ARG BUILD_DATE
ARG VCS_REF

# 定义运行时环境变量（ENV - 在容器运行时可用）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=48080 \
    APP_HOST=127.0.0.1 \
    RELOAD=False

# 安装依赖（先复制requirements，利用Docker缓存）
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install uv && \
    uv sync

# 复制项目代码（排除敏感文件，通过.gitignore）
COPY . .

# 暴露端口（使用环境变量，默认48005）
EXPOSE ${APP_HOST}
EXPOSE ${APP_PORT}

CMD ["python", "main.py"]