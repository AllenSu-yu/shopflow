import os
from dotenv import load_dotenv

# 自動尋找同目錄下的 .env 檔案
load_dotenv()

# 取得目前檔案所在的目錄路徑
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 環境判斷：development 或 production
    # 開發環境：使用 SQLite + 本地檔案
    # 生產環境：使用 RDS PostgreSQL + S3
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
    IS_PRODUCTION = ENVIRONMENT == 'production'
    IS_DEVELOPMENT = not IS_PRODUCTION
    
    # 資料庫配置
    # 開發環境：SQLite（本地檔案）
    # 生產環境：PostgreSQL（RDS）
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        if IS_PRODUCTION:
            # 生產環境必須設定 DATABASE_URL
            raise ValueError("生產環境必須設定 DATABASE_URL 環境變數")
        else:
            # 開發環境預設使用 SQLite
            DATABASE_URL = 'sqlite:///' + os.path.join(basedir, 'instance', 'shop.db')
    
    SECRET_KEY = os.getenv('SECRET_KEY') or 'you-will-never-guess'
    
    # CORS 允許的來源網域（用逗號分隔）
    # 開發環境預設允許常見的本地開發網域
    # 生產環境應在 .env 中設定：CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173').split(',')
    
    # S3 配置（生產環境使用）
    AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    # S3 Base URL（用於生成公開 URL）
    # 格式：https://bucket-name.s3.region.amazonaws.com 或自訂 CloudFront URL
    S3_BASE_URL = os.getenv('S3_BASE_URL')
    
    # 檔案儲存模式：'local' 或 's3'
    # 開發環境預設使用本地檔案，生產環境使用 S3
    FILE_STORAGE_MODE = os.getenv('FILE_STORAGE_MODE', 's3' if IS_PRODUCTION else 'local')
    
    # 應用程式設定
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.getenv('APP_PORT', '5000'))
    # 開發環境預設啟用 reload，生產環境關閉
    APP_RELOAD = os.getenv('APP_RELOAD', 'true' if IS_DEVELOPMENT else 'false').lower() == 'true'
    # TapPay 設定
    TAPPAY_APP_ID = os.getenv('TAPPAY_APP_ID', '166540')
    TAPPAY_APP_KEY = os.getenv('TAPPAY_APP_KEY')
    TAPPAY_PARTNER_KEY = os.getenv('TAPPAY_PARTNER_KEY')
    TAPPAY_MERCHANT_ID = os.getenv('TAPPAY_MERCHANT_ID')