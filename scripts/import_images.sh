#!/bin/bash
# 导入 Docker 镜像脚本
# 用于在离线环境中导入已导出的镜像

set -e

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <镜像文件路径>"
    echo "示例: $0 ./docker_images/images_20240101_120000.tar.gz"
    exit 1
fi

IMPORT_FILE="$1"

# 检查文件是否存在
if [[ ! -e "${IMPORT_FILE}" ]]; then
    echo "错误: 文件不存在: ${IMPORT_FILE}"
    exit 1
fi

if [[ ! -f "${IMPORT_FILE}" ]]; then
    echo "错误: 文件类型错误: ${IMPORT_FILE}"
    echo "请检查文件是否为压缩文件, 或者文件路径是否正确"
    exit 1
fi

echo "开始导入 Docker 镜像..."
echo "镜像文件: ${IMPORT_FILE}"

# 如果是压缩文件，先解压
TEMP_TAR=""
if [[ "${IMPORT_FILE}" == *.gz ]]; then
    echo "解压镜像文件..."
    TEMP_TAR="${IMPORT_FILE%.gz}"
    gunzip -c "${IMPORT_FILE}" > "${TEMP_TAR}"
    IMPORT_FILE="${TEMP_TAR}"
fi

# 导入镜像
echo "正在导入镜像（这可能需要几分钟）..."
docker load -i "${IMPORT_FILE}"

# 清理临时文件
if [ -n "${TEMP_TAR}" ] && [ -f "${TEMP_TAR}" ]; then
    rm -f "${TEMP_TAR}"
fi

echo ""
echo "=========================================="
echo "镜像导入完成!"
echo "=========================================="
echo "已导入的镜像:"
docker images | grep -E "(mysql|redis|fastapi)" || docker images
echo ""
echo "现在可以使用 docker-compose 启动服务:"
echo "  docker-compose up -d"
echo "=========================================="
