# PowerShell 脚本：导入 Docker 镜像
# 用于在离线环境中导入已导出的镜像

param(
    [Parameter(Mandatory=$true)]
    [string]$ImageFile
)

$ErrorActionPreference = "Stop"

# 检查文件是否存在
if (-not (Test-Path $ImageFile)) {
    Write-Host "错误: 文件不存在: $ImageFile" -ForegroundColor Red
    exit 1
}

Write-Host "开始导入 Docker 镜像..." -ForegroundColor Green
Write-Host "镜像文件: $ImageFile" -ForegroundColor Cyan

# 如果是压缩文件，先解压
$TempTar = ""
if ($ImageFile -match '\.gz$') {
    Write-Host "解压镜像文件..." -ForegroundColor Yellow
    $TempTar = $ImageFile -replace '\.gz$', ''
    
    # 尝试使用 gzip 解压
    $gzipAvailable = $false
    try {
        $null = Get-Command gzip -ErrorAction Stop
        $gzipAvailable = $true
    } catch {
        # 尝试使用 7zip
        try {
            $null = Get-Command 7z -ErrorAction Stop
            & 7z x "$ImageFile" -o(Split-Path $TempTar) | Out-Null
            if (Test-Path $TempTar) {
                $ImageFile = $TempTar
            } else {
                Write-Host "错误: 解压失败" -ForegroundColor Red
                exit 1
            }
        } catch {
            Write-Host "错误: 未找到 gzip 或 7zip，无法解压文件" -ForegroundColor Red
            Write-Host "请安装 gzip (通过 WSL/Git Bash) 或 7zip" -ForegroundColor Yellow
            exit 1
        }
    }
    
    if ($gzipAvailable) {
        # 使用 gzip 解压
        & gzip -dc $ImageFile > $TempTar
        if (Test-Path $TempTar) {
            $ImageFile = $TempTar
        } else {
            Write-Host "错误: 解压失败" -ForegroundColor Red
            exit 1
        }
    }
}

# 导入镜像
Write-Host "正在导入镜像（这可能需要几分钟）..." -ForegroundColor Yellow
docker load -i $ImageFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 镜像导入失败" -ForegroundColor Red
    exit 1
}

# 清理临时文件
if (-not [string]::IsNullOrEmpty($TempTar) -and (Test-Path $TempTar)) {
    Remove-Item $TempTar -Force
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "镜像导入完成!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "已导入的镜像:" -ForegroundColor Cyan
docker images | Select-String -Pattern "(mysql|redis|fastapi)" | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "现在可以使用 docker-compose 启动服务:" -ForegroundColor Cyan
Write-Host "  docker-compose up -d" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green
