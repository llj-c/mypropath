# 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装依赖（先复制requirements，利用Docker缓存）
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install uv
RUN uv sync

# 复制项目代码（排除敏感文件，通过.gitignore）
COPY . .

# 暴露端口（与配置一致）
EXPOSE 8080

# 启动命令（通过环境变量指定配置）
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${APP_PORT:-8080} --reload=${RELOAD:-False}"]