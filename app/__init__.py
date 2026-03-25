from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sys
import os

# 導入 config (config.py 位於 app/，與 __init__.py 同層級)
from .config import Config

# 建立資料庫引擎
# 根據資料庫類型自動設定 connect_args
# SQLite 需要 check_same_thread=False 以支援多執行緒環境
# PostgreSQL 等其他資料庫不需要此參數
connect_args = {}
if Config.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False} # SQLite 預設只允許在同一個執行緒中使用同一個連線，FastAPI 使用多執行緒處理請求

engine = create_engine(
    Config.DATABASE_URL,
    connect_args=connect_args # 用來傳遞資料庫驅動程式的額外連線參數，空字典也沒問題
)

# 建立 SessionLocal 類別
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立 Base 類別用於模型定義 (提供 ORM 功能：將 Python 類別映射到資料庫表格)
Base = declarative_base()

# 建立 FastAPI 應用
app = FastAPI(title="ShopFlow API", version="1.0.0")

# 設定 CORS
# 注意：當 allow_credentials=True 時，不能使用 allow_origins=["*"]
# 必須指定具體的網域列表
# 開發環境：允許常見的本地開發網域（從 Config 讀取，可在 .env 中設定）
# 生產環境：在 .env 中設定 CORS_ORIGINS 環境變數
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,  # 從 Config 讀取，統一管理配置
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料庫依賴注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 設定靜態檔案服務（用於提供上傳的圖片）
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 設定模板引擎
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# 註冊路由（必須在 get_db 定義之後，避免循環導入）
from .controllers import (
    admin_router,
    customer_router,
    page_router,
    merchant_router,
    global_router,
    admin_global_router
)

# 全局 API（例如：商店註冊 /api/merchant/register）
app.include_router(global_router, prefix="/api", tags=["global"])

# 全局頁面 (例如: /merchant/register)
app.include_router(merchant_router, prefix="/merchant", tags=["global_pages"])

# 全局後台頁面 (例如: /shop/admin/login)
app.include_router(admin_global_router, prefix="/shop/admin", tags=["admin_global_pages"])

# 前台 API (綁定特定商店 /api/shop/{store_slug}/...)
app.include_router(customer_router, prefix="/api/shop/{store_slug}", tags=["customer"])

# 後台 API (綁定特定商店 /api/shop/{store_slug}/admin/...)
app.include_router(admin_router, prefix="/api/shop/{store_slug}/admin", tags=["admin"])

# 頁面路由 (前台: /shop/{store_slug}/... , 後台: /shop/{store_slug}/admin/...)
app.include_router(page_router, prefix="/shop/{store_slug}", tags=["pages"])

# 應用啟動時初始化資料庫（建立資料表）
@app.on_event("startup")
async def startup_event():
    # 導入模型以確保所有模型都被註冊到 Base.metadata
    from .models import (
        Category,
        Product, ProductImage, ProductSpecGroup, ProductSpecValue, ProductVariant,
        User, Customer,
        Order, OrderItem,
        Cart, CartItem,
        Carousel, StoreInfo
    )
    # 建立所有資料表（如果不存在）
    Base.metadata.create_all(bind=engine)
