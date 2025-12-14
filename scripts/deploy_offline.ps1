# PowerShell 脚本：离线环境一键部署
# 整合了代码拉取和镜像导入功能
# 用法: .\deploy_offline.ps1 [仓库地址] [镜像文件路径]

param(
    [Parameter(Position=0)]
    [string]$RepoUrl = "",
    
    [Parameter(Position=1)]
    [string]$ImageFile = ""
)

$ErrorActionPreference = "Stop"

# 获取项目目录
$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "========================================" -ForegroundColor Green
Write-Host "离线环境一键部署脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 步骤1: 处理代码仓库
Write-Host "[步骤 1/3] 检查代码仓库..." -ForegroundColor Yellow

$IsGitRepo = Test-Path (Join-Path $ProjectDir ".git")

if ($IsGitRepo) {
    Write-Host "✓ 当前目录已经是 Git 仓库" -ForegroundColor Green
    
    if ($RepoUrl) {
        Write-Host "检测到仓库地址参数，更新远程仓库..." -ForegroundColor Yellow
        try {
            $existingRemote = git remote get-url origin 2>$null
            if ($LASTEXITCODE -eq 0) {
                git remote set-url origin $RepoUrl
            } else {
                git remote add origin $RepoUrl
            }
        } catch {
            git remote add origin $RepoUrl
        }
        
        Write-Host "拉取最新代码..." -ForegroundColor Yellow
        git pull origin main 2>$null
        if ($LASTEXITCODE -ne 0) {
            git pull origin master 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "警告: 拉取代码失败，使用当前代码" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "提示: 如需更新代码，请运行: git pull" -ForegroundColor Yellow
    }
} else {
    if (-not $RepoUrl) {
        Write-Host "错误: 当前目录不是 Git 仓库，且未提供仓库地址" -ForegroundColor Red
        Write-Host ""
        Write-Host "用法:" -ForegroundColor Green
        Write-Host "  .\deploy_offline.ps1 [仓库地址] [镜像文件路径]"
        Write-Host ""
        Write-Host "示例:" -ForegroundColor Green
        Write-Host "  .\deploy_offline.ps1 https://github.com/user/repo.git .\docker_images\images_20240101_120000.tar.gz"
        Write-Host "  .\deploy_offline.ps1 https://github.com/user/repo.git  # 自动查找镜像文件"
        exit 1
    }
    
    Write-Host "从仓库拉取代码: $RepoUrl" -ForegroundColor Green
    
    # 检查目录是否为空
    $dirItems = Get-ChildItem $ProjectDir -Force | Where-Object { $_.Name -ne '.git' }
    if ($dirItems.Count -gt 0) {
        $response = Read-Host "警告: 当前目录不为空，是否继续? (y/n)"
        if ($response -notmatch '^[Yy]$') {
            Write-Host "已取消" -ForegroundColor Yellow
            exit 0
        }
    }
    
    # 克隆或拉取仓库
    if ($IsGitRepo) {
        git pull origin main 2>$null
        if ($LASTEXITCODE -ne 0) {
            git pull origin master 2>$null
        }
    } else {
        $ParentDir = Split-Path -Parent $ProjectDir
        $TempDir = Join-Path $ParentDir "temp_repo_$PID"
        
        git clone $RepoUrl $TempDir
        Copy-Item -Path "$TempDir\*" -Destination $ProjectDir -Recurse -Force
        Copy-Item -Path "$TempDir\.*" -Destination $ProjectDir -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $TempDir -Recurse -Force
        
        Write-Host "✓ 代码拉取完成" -ForegroundColor Green
    }
}

# 进入项目目录
Set-Location $ProjectDir

# 步骤2: 查找或验证镜像文件
Write-Host ""
Write-Host "[步骤 2/3] 查找镜像文件..." -ForegroundColor Yellow

if (-not $ImageFile) {
    # 自动查找镜像文件
    $ImageDir = Join-Path $ProjectDir "docker_images"
    
    if (-not (Test-Path $ImageDir)) {
        Write-Host "错误: 未找到 docker_images 目录" -ForegroundColor Red
        Write-Host "请将镜像文件放到 docker_images 目录，或通过参数指定镜像文件路径"
        exit 1
    }
    
    # 查找最新的镜像文件
    $LatestImage = Get-ChildItem -Path $ImageDir -Filter "images_*.tar.gz" -File | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -First 1
    
    if (-not $LatestImage) {
        # 尝试查找未压缩的 tar 文件
        $LatestImage = Get-ChildItem -Path $ImageDir -Filter "images_*.tar" -File | 
            Sort-Object LastWriteTime -Descending | 
            Select-Object -First 1
    }
    
    if (-not $LatestImage) {
        Write-Host "错误: 未找到镜像文件" -ForegroundColor Red
        Write-Host "请将镜像文件放到 docker_images 目录，或通过参数指定:"
        Write-Host "  .\deploy_offline.ps1 [仓库地址] <镜像文件路径>"
        exit 1
    }
    
    $ImageFile = $LatestImage.FullName
    Write-Host "✓ 自动找到镜像文件: $ImageFile" -ForegroundColor Green
} else {
    # 使用提供的镜像文件路径
    if (-not (Test-Path $ImageFile)) {
        # 尝试相对路径
        $FullPath = Join-Path $ProjectDir $ImageFile
        if (Test-Path $FullPath) {
            $ImageFile = $FullPath
        } else {
            Write-Host "错误: 镜像文件不存在: $ImageFile" -ForegroundColor Red
            exit 1
        }
    }
    $ImageFile = (Resolve-Path $ImageFile).Path
    Write-Host "✓ 使用指定的镜像文件: $ImageFile" -ForegroundColor Green
}

# 步骤3: 导入镜像
Write-Host ""
Write-Host "[步骤 3/3] 导入 Docker 镜像..." -ForegroundColor Yellow

# 检查 Docker 是否运行
try {
    docker info | Out-Null
} catch {
    Write-Host "错误: Docker 未运行或无法访问" -ForegroundColor Red
    Write-Host "请确保 Docker 已启动"
    exit 1
}

# 调用导入脚本
$ImportScript = Join-Path $ProjectDir "scripts\import_images.ps1"

if (-not (Test-Path $ImportScript)) {
    Write-Host "错误: 未找到导入脚本: $ImportScript" -ForegroundColor Red
    exit 1
}

# 执行导入
& $ImportScript $ImageFile

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "部署完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Cyan
Write-Host "1. 检查已导入的镜像:"
Write-Host "   docker images" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. 配置环境变量（如未配置）:"
Write-Host "   Copy-Item .env.example .env" -ForegroundColor Yellow
Write-Host "   # 编辑 .env 文件" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. 启动服务:"
Write-Host "   docker compose -f docker-compose.offline.yaml up -d" -ForegroundColor Yellow
Write-Host ""
Write-Host "提示:" -ForegroundColor Cyan
Write-Host "- 如果 FastAPI 镜像名称与配置不同，请修改 docker-compose.offline.yaml"
Write-Host "- 或使用命令打标签: docker tag <实际镜像名> pyt-fastapi:latest"
Write-Host ""
