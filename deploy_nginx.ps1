# Nginx 部署腳本（PowerShell）
# 自動安裝和配置 Nginx 反向代理

param(
    [Parameter(Mandatory=$true)]
    [string]$EC2IP,
    
    [Parameter(Mandatory=$true)]
    [string]$KeyPath,
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "ubuntu"  # Amazon Linux 使用 "ec2-user"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Nginx 反向代理部署腳本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$configFile = "deployment\nginx\shopflow.conf.production"

if (-not (Test-Path $configFile)) {
    Write-Host "[錯誤] 找不到配置檔案：$configFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $KeyPath)) {
    Write-Host "[錯誤] 找不到金鑰檔案：$KeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "EC2 IP: $EC2IP" -ForegroundColor Green
Write-Host "使用者名稱: $Username" -ForegroundColor Green
Write-Host ""

# 步驟 1：檢查 Nginx 是否已安裝
Write-Host "[步驟 1/6] 檢查 Nginx..." -ForegroundColor Yellow
$nginxCheck = ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "which nginx 2>/dev/null || echo 'not_installed'"

if ($nginxCheck -match "not_installed") {
    Write-Host "  安裝 Nginx..." -ForegroundColor Gray
    ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" @"
        sudo apt-get update -qq
        sudo apt-get install -y nginx
    "@
    Write-Host "  [成功] Nginx 安裝完成" -ForegroundColor Green
} else {
    Write-Host "  Nginx 已安裝：$nginxCheck" -ForegroundColor Green
}

# 步驟 2：上傳配置檔案
Write-Host "[步驟 2/6] 上傳配置檔案..." -ForegroundColor Yellow
scp -i $KeyPath -o StrictHostKeyChecking=no $configFile "$Username@$EC2IP`:/tmp/shopflow.conf"

# 步驟 3：移動配置檔案到正確位置
Write-Host "[步驟 3/6] 配置 Nginx..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" @"
    # 備份現有配置（如果存在）
    sudo cp /etc/nginx/sites-available/shopflow.conf /etc/nginx/sites-available/shopflow.conf.backup 2>/dev/null || true
    
    # 移動新配置
    sudo mv /tmp/shopflow.conf /etc/nginx/sites-available/shopflow.conf
    
    # 建立符號連結（Ubuntu）
    sudo ln -sf /etc/nginx/sites-available/shopflow.conf /etc/nginx/sites-enabled/shopflow.conf
    
    # 移除預設配置（如果存在）
    sudo rm -f /etc/nginx/sites-enabled/default
"@

# 步驟 4：測試配置
Write-Host "[步驟 4/6] 測試 Nginx 配置..." -ForegroundColor Yellow
$testResult = ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "sudo nginx -t 2>&1"

if ($testResult -match "successful") {
    Write-Host "  [成功] 配置檔案語法正確" -ForegroundColor Green
} else {
    Write-Host "  [錯誤] 配置檔案語法錯誤：" -ForegroundColor Red
    Write-Host $testResult -ForegroundColor Red
    exit 1
}

# 步驟 5：啟動 Nginx
Write-Host "[步驟 5/6] 啟動 Nginx..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" @"
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    sudo systemctl status nginx --no-pager | head -5
"@

# 步驟 6：驗證
Write-Host "[步驟 6/6] 驗證部署..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$nginxStatus = ssh -i $KeyPath -o StrictHostKeyChecking=no "$Username@$EC2IP" "sudo systemctl is-active nginx"
if ($nginxStatus -eq "active") {
    Write-Host "  [成功] Nginx 正在運行" -ForegroundColor Green
} else {
    Write-Host "  [警告] Nginx 狀態：$nginxStatus" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[完成] Nginx 部署完成！" -ForegroundColor Green
Write-Host ""
Write-Host "測試指令：" -ForegroundColor Cyan
Write-Host "  # 在 EC2 上測試" -ForegroundColor White
Write-Host "  curl http://localhost" -ForegroundColor White
Write-Host ""
Write-Host "  # 從外部測試（需要 DNS 設定）" -ForegroundColor White
Write-Host "  curl http://myshoppingdemo.store" -ForegroundColor White
Write-Host "  curl http://admin.myshoppingdemo.store" -ForegroundColor White
Write-Host ""
Write-Host "查看日誌：" -ForegroundColor Cyan
Write-Host "  sudo tail -f /var/log/nginx/shopflow_access.log" -ForegroundColor White
Write-Host "  sudo tail -f /var/log/nginx/shopflow_error.log" -ForegroundColor White
Write-Host ""
Write-Host "管理指令：" -ForegroundColor Cyan
Write-Host "  sudo systemctl status nginx    # 查看狀態" -ForegroundColor White
Write-Host "  sudo systemctl restart nginx    # 重啟 Nginx" -ForegroundColor White
Write-Host "  sudo nginx -t                   # 測試配置" -ForegroundColor White
