# 离线环境部署指南

本指南说明如何在离线环境中部署已构建好的 Docker 环境。

## 方案概述

1. **在已构建的机器上**: 导出所有 Docker 镜像
2. **传输镜像文件**: 将导出的镜像文件传输到离线环境
3. **在离线环境中**: 导入镜像并使用离线配置启动服务

## 步骤说明

### 第一步: 在已构建的机器上导出镜像

#### Windows 环境

```powershell
# 进入项目目录
cd d:\code\temp\pyt

# 运行导出脚本
.\scripts\export_images.ps1
```

#### Linux/Mac 环境

```bash
# 进入项目目录
cd /path/to/pyt

# 给脚本添加执行权限
chmod +x scripts/export_images.sh

# 运行导出脚本
./scripts/export_images.sh
```

导出完成后，会在 `docker_images` 目录下生成一个压缩的镜像文件，例如: `images_20240101_120000.tar.gz`

### 第二步: 传输镜像文件

将导出的镜像文件（`docker_images/images_*.tar.gz`）传输到离线环境，可以使用以下方式:

- U盘/移动硬盘
- 内网文件服务器
- 其他物理传输方式

### 第三步: 在离线环境中导入镜像

#### Windows 环境

```powershell
# 进入项目目录
cd d:\code\temp\pyt

# 运行导入脚本（替换为实际的镜像文件路径）
.\scripts\import_images.ps1 .\docker_images\images_20240101_120000.tar.gz
```

#### Linux/Mac 环境

```bash
# 进入项目目录
cd /path/to/pyt

# 给脚本添加执行权限
chmod +x scripts/import_images.sh

# 运行导入脚本（替换为实际的镜像文件路径）
./scripts/import_images.sh ./docker_images/images_20240101_120000.tar.gz
```

### 第四步: 检查导入的镜像

```bash
# 查看已导入的镜像
docker images
```

确认以下镜像已存在:
- `mysql:8.0`
- `redis:7-alpine`
- `pyt-fastapi:latest` (或类似名称)

### 第五步: 配置环境变量

确保在离线环境中配置了 `.env` 文件，包含所有必要的环境变量。

### 第六步: 使用离线配置启动服务

```bash
# 使用离线版本的 docker-compose 配置
docker-compose -f docker-compose.offline.yaml up -d
```

**注意**: 如果导入的 FastAPI 镜像名称与 `docker-compose.offline.yaml` 中的不同，需要先修改该文件中的 `image` 字段。

## 常见问题

### 1. FastAPI 镜像名称不匹配

如果导入后 FastAPI 镜像的名称与配置文件中不同，有两种解决方案:

**方案 A**: 修改 `docker-compose.offline.yaml` 中的镜像名称

```yaml
fastapi:
  image: <实际的镜像名称>  # 修改这里
```

**方案 B**: 给导入的镜像打标签

```bash
# 查看实际镜像名称
docker images

# 给镜像打标签（假设实际名称是 other-name:latest）
docker tag other-name:latest pyt-fastapi:latest
```

### 2. 镜像文件太大

如果镜像文件太大，可以考虑:

1. **分别导出**: 修改导出脚本，分别导出每个镜像
2. **使用压缩**: 脚本已自动使用 gzip 压缩
3. **清理未使用的镜像**: 在导出前清理不需要的镜像

### 3. 验证导入是否成功

```bash
# 检查镜像是否存在
docker images | grep -E "(mysql|redis|fastapi)"

# 测试启动（不实际启动）
docker-compose -f docker-compose.offline.yaml config
```

## 手动操作（如果脚本不可用）

如果脚本无法运行，可以手动执行:

### 导出镜像

```bash
# 导出所有需要的镜像
docker save mysql:8.0 redis:7-alpine pyt-fastapi:latest -o images.tar

# 压缩（可选）
gzip images.tar
```

### 导入镜像

```bash
# 解压（如果压缩了）
gunzip images.tar.gz

# 导入
docker load -i images.tar
```

## 注意事项

1. **数据持久化**: 离线环境中的数据卷配置与在线环境相同，数据会持久化保存
2. **网络配置**: 确保离线环境中的网络配置（端口映射等）符合实际需求
3. **环境变量**: 确保 `.env` 文件在离线环境中正确配置
4. **镜像版本**: 建议在导出和导入时记录镜像版本，便于后续维护
