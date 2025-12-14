#!/bin/bash
# 离线环境一键部署脚本
# 整合了代码拉取和镜像导入功能
# 用法: ./deploy_offline.sh [仓库地址] [镜像文件路径]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_URL="${1:-}"
IMAGE_FILE="${2:-}"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}离线环境一键部署脚本${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 步骤1: 处理代码仓库
echo -e "${YELLOW}[步骤 1/3] 检查代码仓库...${NC}"

if [ -d "${PROJECT_DIR}/.git" ]; then
    echo -e "${GREEN}✓${NC} 当前目录已经是 Git 仓库"
    
    if [ -n "${REPO_URL}" ]; then
        echo -e "${YELLOW}检测到仓库地址参数，更新远程仓库...${NC}"
        git remote set-url origin "${REPO_URL}" 2>/dev/null || git remote add origin "${REPO_URL}"
        echo -e "${YELLOW}拉取最新代码...${NC}"
        git pull origin main || git pull origin master || echo -e "${YELLOW}警告: 拉取代码失败，使用当前代码${NC}"
    else
        echo -e "${CYAN}提示: 如需更新代码，请运行: git pull${NC}"
    fi
else
    if [ -z "${REPO_URL}" ]; then
        echo -e "${RED}错误: 当前目录不是 Git 仓库，且未提供仓库地址${NC}"
        echo ""
        echo "用法:"
        echo "  $0 [仓库地址] [镜像文件路径]"
        echo ""
        echo "示例:"
        echo "  $0 https://github.com/user/repo.git ./docker_images/images_20240101_120000.tar.gz"
        echo "  $0 https://github.com/user/repo.git  # 自动查找镜像文件"
        echo "  $0  # 如果当前目录已经是仓库，只需提供镜像文件路径"
        exit 1
    fi
    
    echo -e "${YELLOW}从仓库拉取代码: ${REPO_URL}${NC}"
    
    # 如果当前目录有文件，询问是否继续
    if [ "$(ls -A "${PROJECT_DIR}" 2>/dev/null | grep -v '^\.git$')" ]; then
        echo -e "${YELLOW}警告: 当前目录不为空，是否继续? (y/n)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "已取消"
            exit 0
        fi
    fi
    
    # 克隆仓库
    if [ -d "${PROJECT_DIR}/.git" ] || [ -n "$(ls -A "${PROJECT_DIR}" 2>/dev/null)" ]; then
        # 如果已经有 .git 目录或目录不为空，尝试拉取
        if [ -d "${PROJECT_DIR}/.git" ]; then
            git pull origin main || git pull origin master || true
        fi
    else
        # 克隆到父目录，然后移动到当前目录
        PARENT_DIR="$(dirname "${PROJECT_DIR}")"
        TEMP_DIR="${PARENT_DIR}/temp_repo_$$"
        git clone "${REPO_URL}" "${TEMP_DIR}"
        mv "${TEMP_DIR}"/* "${TEMP_DIR}"/.[!.]* "${PROJECT_DIR}"/ 2>/dev/null || true
        rm -rf "${TEMP_DIR}"
    fi
    
    echo -e "${GREEN}✓${NC} 代码拉取完成"
fi

# 进入项目目录
cd "${PROJECT_DIR}"

# 步骤2: 查找或验证镜像文件
echo ""
echo -e "${YELLOW}[步骤 2/3] 查找镜像文件...${NC}"

if [ -z "${IMAGE_FILE}" ]; then
    # 自动查找镜像文件
    IMAGE_DIR="${PROJECT_DIR}/docker_images"
    
    if [ ! -d "${IMAGE_DIR}" ]; then
        echo -e "${RED}错误: 未找到 docker_images 目录${NC}"
        echo "请将镜像文件放到 docker_images 目录，或通过参数指定镜像文件路径"
        exit 1
    fi
    
    # 查找最新的镜像文件
    LATEST_IMAGE=$(find "${IMAGE_DIR}" -name "images_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    
    if [ -z "${LATEST_IMAGE}" ]; then
        # 尝试查找未压缩的 tar 文件
        LATEST_IMAGE=$(find "${IMAGE_DIR}" -name "images_*.tar" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    fi
    
    if [ -z "${LATEST_IMAGE}" ]; then
        echo -e "${RED}错误: 未找到镜像文件${NC}"
        echo "请将镜像文件放到 docker_images 目录，或通过参数指定:"
        echo "  $0 [仓库地址] <镜像文件路径>"
        exit 1
    fi
    
    IMAGE_FILE="${LATEST_IMAGE}"
    echo -e "${GREEN}✓${NC} 自动找到镜像文件: ${IMAGE_FILE}"
else
    # 使用提供的镜像文件路径
    if [ ! -f "${IMAGE_FILE}" ]; then
        # 尝试相对路径
        if [ -f "${PROJECT_DIR}/${IMAGE_FILE}" ]; then
            IMAGE_FILE="${PROJECT_DIR}/${IMAGE_FILE}"
        else
            echo -e "${RED}错误: 镜像文件不存在: ${IMAGE_FILE}${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}✓${NC} 使用指定的镜像文件: ${IMAGE_FILE}"
fi

# 步骤3: 导入镜像
echo ""
echo -e "${YELLOW}[步骤 3/3] 导入 Docker 镜像...${NC}"

# 检查 Docker 是否运行
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}错误: Docker 未运行或无法访问${NC}"
    echo "请确保 Docker 已启动"
    exit 1
fi

# 调用导入脚本
IMPORT_SCRIPT="${PROJECT_DIR}/scripts/import_images.sh"

if [ ! -f "${IMPORT_SCRIPT}" ]; then
    echo -e "${RED}错误: 未找到导入脚本: ${IMPORT_SCRIPT}${NC}"
    exit 1
fi

# 确保脚本有执行权限
chmod +x "${IMPORT_SCRIPT}"

# 执行导入
"${IMPORT_SCRIPT}" "${IMAGE_FILE}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}下一步操作:${NC}"
echo "1. 检查已导入的镜像:"
echo -e "   ${YELLOW}docker images${NC}"
echo ""
echo "2. 配置环境变量（如未配置）:"
echo -e "   ${YELLOW}cp .env.example .env${NC}"
echo -e "   ${YELLOW}# 编辑 .env 文件${NC}"
echo ""
echo "3. 启动服务:"
echo -e "   ${YELLOW}docker compose -f docker-compose.offline.yaml up -d${NC}"
echo ""
echo -e "${CYAN}提示:${NC}"
echo "- 如果 FastAPI 镜像名称与配置不同，请修改 docker-compose.offline.yaml"
echo "- 或使用命令打标签: docker tag <实际镜像名> pyt-fastapi:latest"
echo ""
