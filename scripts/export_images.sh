#!/bin/bash
# 导出 Docker 镜像脚本
# 用于在已构建的环境中导出所有需要的镜像，便于离线部署

set -e

# 配置
EXPORT_DIR="./docker_images"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPORT_FILE="${EXPORT_DIR}/images_${TIMESTAMP}.tar"

# 创建导出目录
mkdir -p "${EXPORT_DIR}"

echo "开始导出 Docker 镜像..."

# 获取所有需要的镜像名称
# 1. MySQL 镜像
MYSQL_IMAGE="mysql:8.0"

# 2. Redis 镜像
REDIS_IMAGE="redis:7-alpine"

# 3. FastAPI 镜像（需要先构建或获取）
# 方法1: 尝试从 docker compose 获取实际镜像名（如果已经构建过）
FASTAPI_IMAGE=""
if command -v docker compose &> /dev/null; then
    FASTAPI_IMAGE=$(docker compose images fastapi 2>/dev/null | tail -n +2 | awk 'NF>=3{print $2":"$3}' | head -1 | tr -d ' ')
fi

# 方法2: 如果方法1失败，尝试使用项目名构建镜像名
if [ -z "${FASTAPI_IMAGE}" ] || [ "${FASTAPI_IMAGE}" = ":" ] || [ "${FASTAPI_IMAGE}" = "" ]; then
    # 获取项目名,, 将大写转为小写, 同时去除非字母数字和连字符的字符
    COMPOSE_PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-')
    FASTAPI_IMAGE="${COMPOSE_PROJECT_NAME}-fastapi:latest"
fi

# 方法3: 检查镜像是否存在，如果不存在则尝试构建
if ! docker image inspect "${FASTAPI_IMAGE}" &>/dev/null 2>&1; then
    echo "FastAPI 镜像不存在，尝试构建..."
    if command -v docker compose &> /dev/null; then
        docker compose build fastapi
        # 构建后再次尝试获取镜像名
        FASTAPI_IMAGE=$(docker compose images fastapi 2>/dev/null | tail -n +3 | awk '{print $2":"$3}' | head -1 | tr -d ' ')
        if [ -z "${FASTAPI_IMAGE}" ] || [ "${FASTAPI_IMAGE}" = ":" ]; then
            COMPOSE_PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-')
            FASTAPI_IMAGE="${COMPOSE_PROJECT_NAME}-fastapi:latest"
        fi
    else
        echo "错误: 无法找到 docker-compose，请手动构建镜像:"
        echo "  docker compose build fastapi"
        exit 1
    fi
    
    # 最终检查
    if ! docker image inspect "${FASTAPI_IMAGE}" &>/dev/null 2>&1; then
        echo "错误: 无法找到或构建 FastAPI 镜像"
        echo "请手动构建: docker compose build fastapi"
        echo "或检查镜像名称: docker images | grep fastapi"
        exit 1
    fi
fi


echo "准备导出以下镜像:"
echo "  - ${MYSQL_IMAGE}"
echo "  - ${REDIS_IMAGE}"
echo "  - ${FASTAPI_IMAGE}"

# 导出所有镜像到单个 tar 文件
docker save \
    "${MYSQL_IMAGE}" \
    "${REDIS_IMAGE}" \
    "${FASTAPI_IMAGE}" \
    -o "${EXPORT_FILE}"

# 压缩镜像文件（可选，减小体积）
echo "压缩镜像文件..."
gzip -f "${EXPORT_FILE}"
COMPRESSED_FILE="${EXPORT_FILE}.gz"

# 计算文件大小
FILE_SIZE=$(du -h "${COMPRESSED_FILE}" | cut -f1)

echo ""
echo "=========================================="
echo "镜像导出完成!"
echo "=========================================="
echo "导出文件: ${COMPRESSED_FILE}"
echo "文件大小: ${FILE_SIZE}"
echo ""
echo "请将此文件传输到离线环境，然后运行导入脚本:"
echo "  ./scripts/import_images.sh ${COMPRESSED_FILE}"
echo "=========================================="
