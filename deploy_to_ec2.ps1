# EC2 部署腳本（PowerShell）
# 自動上傳專案檔案並執行部署

param(
    [Parameter(Mandatory=$true)]
    [string]$EC2IP,
    
    [Parameter(Mandatory=$true)]
    [string]$KeyPath,
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "ubuntu",  # Amazon Linux 使用 "ec2-user"
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectPath = "/home/ubuntu/shopflow"  # Amazon Linux 使用 "/home/ec2-user/shopflow"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "ShopFlow EC2 部署腳本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查必要檔案
$requiredFiles = @("Dockerfile", ".dockerignore", "app")
$missingFiles = @()

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "[錯誤] 找不到必要檔案：" -ForegroundColor Red
    foreach ($file in $missingFiles) {
        Write-Host "  - $file" -ForegroundColor Red
    }
    exit 1
}

if (-not (Test-Path $KeyPath)) {
    Write-Host "[錯誤] 找不到金鑰檔案：$KeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "EC2 IP: $EC2IP" -ForegroundColor Green
Write-Host "使用者名稱: $Username" -ForegroundColor Green
Write-Host "專案路徑: $ProjectPath" -ForegroundColor Green
Write-Host ""

# 步驟 1：建立遠端目錄
Write-Host "[步驟 1/5] 建立遠端目錄..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "mkdir -p $ProjectPath"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[錯誤] 無法連線到 EC2" -ForegroundColor Red
    exit 1
}

# 步驟 2：上傳檔案
Write-Host "[步驟 2/5] 上傳專案檔案..." -ForegroundColor Yellow
Write-Host "  上傳 app/ 目錄..." -ForegroundColor Gray
scp -r -i $KeyPath -o StrictHostKeyChecking=no app "$Username@$EC2IP`:$ProjectPath/"

Write-Host "  上傳 Dockerfile..." -ForegroundColor Gray
scp -i $KeyPath -o StrictHostKeyChecking=no Dockerfile "$Username@$EC2IP`:$ProjectPath/"

Write-Host "  上傳 .dockerignore..." -ForegroundColor Gray
scp -i $KeyPath -o StrictHostKeyChecking=no .dockerignore "$Username@$EC2IP`:$ProjectPath/"

Write-Host "  上傳 .env.production..." -ForegroundColor Gray
if (Test-Path ".env.production") {
    scp -i $KeyPath -o StrictHostKeyChecking=no .env.production "$Username@$EC2IP`:$ProjectPath/"
} else {
    Write-Host "  [警告] .env.production 不存在，請手動建立" -ForegroundColor Yellow
}

# 步驟 3：檢查 Docker 是否安裝
Write-Host "[步驟 3/5] 檢查 Docker..." -ForegroundColor Yellow
$dockerCheck = ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "docker --version 2>&1"
if ($dockerCheck -match "Docker version") {
    Write-Host "  Docker 已安裝：$dockerCheck" -ForegroundColor Green
} else {
    Write-Host "  [警告] Docker 可能未安裝，部署可能會失敗" -ForegroundColor Yellow
}

# 步驟 4：建立 Docker 映像
Write-Host "[步驟 4/5] 建立 Docker 映像（這可能需要幾分鐘）..." -ForegroundColor Yellow
Write-Host "  執行：docker build -t shopflow:latest ." -ForegroundColor Gray
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "cd $ProjectPath && docker build -t shopflow:latest ."

if ($LASTEXITCODE -ne 0) {
    Write-Host "[錯誤] Docker 映像建立失敗" -ForegroundColor Red
    Write-Host "  請檢查錯誤訊息並手動執行：" -ForegroundColor Yellow
    Write-Host "  ssh -i `"$KeyPath`" $Username@$EC2IP" -ForegroundColor White
    Write-Host "  cd $ProjectPath" -ForegroundColor White
    Write-Host "  docker build -t shopflow:latest ." -ForegroundColor White
    exit 1
}

# 步驟 5：停止舊容器（如果存在）
Write-Host "[步驟 5/5] 停止舊容器（如果存在）..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "docker stop shopflow-app 2>/dev/null; docker rm shopflow-app 2>/dev/null; true"

# 步驟 6：啟動新容器
Write-Host "[步驟 6/6] 啟動 Docker 容器..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" @"
cd $ProjectPath
docker run -d \
  --name shopflow-app \
  --env-file .env.production \
  -p 5000:5000 \
  --restart unless-stopped \
  shopflow:latest
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "[錯誤] 容器啟動失敗" -ForegroundColor Red
    Write-Host "  請檢查錯誤訊息：" -ForegroundColor Yellow
    Write-Host "  ssh -i `"$KeyPath`" $Username@$EC2IP" -ForegroundColor White
    Write-Host "  docker logs shopflow-app" -ForegroundColor White
    exit 1
}

# 等待容器啟動
Write-Host "  等待容器啟動..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# 檢查容器狀態
Write-Host ""
Write-Host "[完成] 部署完成！" -ForegroundColor Green
Write-Host ""
Write-Host "容器狀態：" -ForegroundColor Cyan
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "docker ps | grep shopflow-app"

Write-Host ""
Write-Host "查看日誌：" -ForegroundColor Cyan
Write-Host "  ssh -i `"$KeyPath`" $Username@$EC2IP" -ForegroundColor White
Write-Host "  docker logs shopflow-app" -ForegroundColor White
Write-Host ""
Write-Host "測試應用程式：" -ForegroundColor Cyan
Write-Host "  curl http://localhost:5000" -ForegroundColor White
Write-Host "  或從瀏覽器訪問：http://$EC2IP:5000" -ForegroundColor White
