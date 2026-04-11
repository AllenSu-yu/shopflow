# ShopFlow 多租戶電商平台 (Multi-tenant E-commerce Platform)

ShopFlow 是一個建構於 FastAPI 的多租戶（Multi-tenant）電商平台系統。它允許多個商家在同一平台上建立屬於自己的獨立商店，並提供顧客完整的購物與結帳體驗。

本專案採用前後端分離的概念設計，後端為 Python FastAPI，前端透過 Jinja2 提供初始版面並大量運用 JavaScript (Fetch API) 進行非同步資料載入。這是一套具備完整資料庫架構、認證機制、金流串接以及 AWS 雲端部署解決方案的全端專案。

## 🌟 核心功能 (Features)

### 🏪 商家 (Merchant & Admin)
* **商店註冊與獨立網址**：每間商店擁有獨一無二的 `store_slug` 網域代碼。
* **資料隔離**：不同商店的商品、訂單、顧客與設置完全獨立。
* **後台管理系統**：支援商品管理（多規格配置）、訂單狀態追蹤、商品分類設定以及前台輪播圖等 CMS 設置。
* **圖片上傳**：開發環境支援本地儲存，正式環境無縫切換至 **AWS S3**。

### 🛒 顧客 (Customer)
* **獨立會員系統**：顧客帳號按商店隔離，確保不同商家的顧客資料不會混淆。
* **購物流暢體驗**：非同步載入商品清單與購物車操作，無需頻繁重整頁面。
* **第三方金流串接**：完整串接 **TapPay** 金流，實作符合 PCI DSS 規範的信用卡安全加密支付流程。

## 🛠 技術堆疊 (Tech Stack)

### 後端 (Backend)
* **框架**：[FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)
* **資料庫 ORM**：[SQLAlchemy](https://www.sqlalchemy.org/)
* **資料庫遷移**：[Alembic](https://alembic.sqlalchemy.org/)
* **資料驗證**：[Pydantic](https://docs.pydantic.dev/)
* **開發資料庫**：SQLite
* **正式資料庫**：PostgreSQL (AWS RDS)

### 前端 (Frontend)
* **樣式框架**：[Bootstrap 5](https://getbootstrap.com/)
* **模板引擎**：Jinja2
* **互動邏輯**：Vanilla JavaScript (Fetch API for AJAX)

### 基礎設施與部署 (Infrastructure & Deployment)
* **容器化**：[Docker](https://www.docker.com/)
* **網頁伺服器 / 反向代理**：Nginx
* **雲端架構 (AWS)**：
  * **EC2**：應用程式伺服器
  * **RDS**：PostgreSQL 關聯式資料庫
  * **S3**：靜態圖片儲存
  * **CloudFront**：CDN 內容分發加速
  * **Route 53**：DNS 解析

## 🏗 系統架構 (System Architecture)

* **分層架構 (Layered Architecture)**：
  1. **Router (`app/__init__.py`)**：路由分配。
  2. **Controller (`app/controllers/`)**：請求驗證與回應（Pydantic）。
  3. **Service (`app/services/`)**：核心商業邏輯（訂單建立、庫存計算等）。
  4. **Model (`app/models/`)**：資料庫 Schema 定義。

* **整體部署架構概覽**：
  使用者 -> Route 53 (DNS) -> Nginx (反向代理 / SSL) -> Docker 容器 (FastAPI/Uvicorn)
  靜態檔案加速 -> CloudFront (CDN) -> S3 (雲端儲存)

## 🚀 本機開發環境設定 (Local Development)

### 1. 複製專案與建立虛擬環境
```bash
git clone <repository_url>
cd shopflow-project
python -m venv .venv
# 啟動虛擬環境 (Windows)
.venv\Scripts\activate
# 啟動虛擬環境 (Mac/Linux)
source .venv/bin/activate
```

### 2. 安裝依賴套件
```bash
pip install -r app/requirements.txt
```

### 3. 環境變數設定
將 `.env.example` 複製一份並重新命名為 `.env`，設定對應的環境變數。本機開發預設使用 SQLite，無需配置 AWS 相關服務金鑰即可運行基本功能。

### 4. 資料庫初始化
使用 Alembic 建立 SQLite 資料庫與資料表：
```bash
alembic upgrade head
```

### 5. 啟動伺服器
```bash
python app/run.py
```
> 伺服器啟動後，請瀏覽：`http://localhost:5000`

## 📦 Docker 部署與 AWS 上線指南
本專案提供完整的 Dockerfile 用於建立生產環境的映像檔。上線到 AWS 的主要步驟包含：
1. **Docker 建置**：`docker build -t shopflow-app .`
2. **Push 至 ECR/Docker Hub**
3. **AWS RDS 設定**：建置 PostgreSQL 並將連線字串放入 `.env.production`
4. **伺服器執行**：在 EC2 上透過 Nginx 代理轉發流量給 Docker 容器 `docker run -p 5000:5000 --env-file .env.production shopflow-app`
*（詳細部署資訊請參考專案文件內的部署指南）*

## 🔒 授權條款 (License)
本專案為自定授權，詳細規範請聯絡作者或參考相關授權協議。
