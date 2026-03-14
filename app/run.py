import uvicorn
import sys
import os

# 確保可以正確導入 app 模組
# 如果從 app 目錄執行，需要將父目錄加入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 導入 Config 以取得環境設定
from app.config import Config

if __name__ == '__main__':
    # 啟動 FastAPI 應用
    # 資料庫會在應用啟動時自動初始化（見 app/__init__.py 的 startup_event）
    uvicorn.run(
        "app:app",
        host=Config.APP_HOST,
        port=Config.APP_PORT,
        reload=Config.APP_RELOAD  # 根據環境變數決定是否啟用自動重載
    )

# 也可以直接使用命令列啟動：
# uvicorn app:app --host 0.0.0.0 --port 5000 --reload
# 注意：使用命令列啟動時，需要從專案根目錄執行
