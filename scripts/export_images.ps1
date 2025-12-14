# PowerShell 脚本：导出 Docker 镜像
# 用于在已构建的环境中导出所有需要的镜像，便于离线部署

$ErrorActionPreference = "Stop"

# 配置
$ExportDir = ".\docker_images"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ExportFile = Join-Path $ExportDir "images_$Timestamp.tar"

# 创建导出目录
if (-not (Test-Path $ExportDir)) {
    New-Item -ItemType Directory -Path $ExportDir | Out-Null
}

Write-Host "开始导出 Docker 镜像..." -ForegroundColor Green

# 获取所有需要的镜像名称
$MysqlImage = "mysql:8.0"
$RedisImage = "redis:7-alpine"

# 获取 FastAPI 镜像名
$ComposeProjectName = (Get-Item .).Name.ToLower() -replace '[^a-z0-9-]', ''
$FastApiImage = "${ComposeProjectName}-fastapi:latest"

# 检查 FastAPI 镜像是否存在
try {
    docker image inspect $FastApiImage 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FastAPI 镜像不存在，尝试从 docker-compose 获取..." -ForegroundColor Yellow
        # 尝试从 docker-compose 获取
        $ComposeImages = docker-compose images fastapi 2>&1
        if ($LASTEXITCODE -eq 0) {
            $FastApiImage = ($ComposeImages | Select-Object -Skip 2 | Select-Object -First 1).Split() | Where-Object { $_ -match ':' } | Select-Object -First 1
        }
        if ([string]::IsNullOrEmpty($FastApiImage)) {
            Write-Host "错误: 无法自动获取 FastAPI 镜像名，请先构建:" -ForegroundColor Red
            Write-Host "  docker-compose build fastapi" -ForegroundColor Yellow
            exit 1
        }
    }
} catch {
    Write-Host "错误: 无法检查 FastAPI 镜像，请先构建:" -ForegroundColor Red
    Write-Host "  docker-compose build fastapi" -ForegroundColor Yellow
    exit 1
}

Write-Host "准备导出以下镜像:" -ForegroundColor Cyan
Write-Host "  - $MysqlImage"
Write-Host "  - $RedisImage"
Write-Host "  - $FastApiImage"

# 导出所有镜像到单个 tar 文件
Write-Host "正在导出镜像..." -ForegroundColor Yellow
docker save $MysqlImage $RedisImage $FastApiImage -o $ExportFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 镜像导出失败" -ForegroundColor Red
    exit 1
}

# 压缩镜像文件
Write-Host "压缩镜像文件..." -ForegroundColor Yellow
$CompressedFile = "$ExportFile.gz"

# 尝试使用 gzip（如果系统有 gzip）
$gzipAvailable = $false
try {
    $null = Get-Command gzip -ErrorAction Stop
    $gzipAvailable = $true
} catch {
    # gzip 不可用，尝试使用 7zip
    try {
        $null = Get-Command 7z -ErrorAction Stop
        & 7z a -tgzip "$CompressedFile" "$ExportFile" | Out-Null
        Remove-Item $ExportFile
    } catch {
        Write-Host "警告: 未找到 gzip 或 7zip，跳过压缩步骤" -ForegroundColor Yellow
        Write-Host "可以使用未压缩的 tar 文件: $ExportFile" -ForegroundColor Yellow
        $CompressedFile = $ExportFile
    }
}

if ($gzipAvailable) {
    # 使用 gzip 压缩（需要 WSL 或 Git Bash）
    & gzip -f $ExportFile
    if (-not (Test-Path $CompressedFile)) {
        Write-Host "警告: gzip 压缩失败，使用未压缩文件" -ForegroundColor Yellow
        $CompressedFile = $ExportFile
    }
}

# 计算文件大小
$FileSize = (Get-Item $CompressedFile).Length / 1MB
$FileSizeFormatted = "{0:N2} MB" -f $FileSize

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "镜像导出完成!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "导出文件: $CompressedFile"
Write-Host "文件大小: $FileSizeFormatted"
Write-Host ""
Write-Host "请将此文件传输到离线环境，然后运行导入脚本:" -ForegroundColor Cyan
Write-Host "  .\scripts\import_images.ps1 $CompressedFile" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green
