# 基础镜像
FROM python:3.11-slim AS base

# 安装uv的最小系统依赖（官方要求）
RUN apt-get update && apt-get install -y --no-install-recommends \   
    ca-certificates
    && rm -rf /var/lib/apt/lists/*  # 清理缓存，减小镜像体积

# 升级pip + 安装指定版本uv
ENV UV_VERSION=0.9.10
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir --upgrade pip  -i ${PIP_INDEX_URL}\
    && pip install --no-cache-dir uv==${UV_VERSION} -i ${PIP_INDEX_URL}


# 验证uv安装（可选，排错用）
RUN uv --version

# 设置工作目录
WORKDIR /app
COPY uv.lock* pyproject.toml ./
RUN uv sync --no-dev --no-install-project
COPY . .

CMD ["uv", "run", "main.py"]