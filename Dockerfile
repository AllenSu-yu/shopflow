FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝 Python 依賴
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY app/ .

# 建立必要的目錄
RUN mkdir -p static/uploads/products static/uploads/carousels instance

# 設定 Python 路徑，確保可以正確導入模組
# 將 /app 加入 Python 路徑，這樣可以正確導入 app 模組
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 5000

# 啟動命令
# 方法 1：使用 run.py（推薦，因為它處理了路徑問題）
CMD ["python", "run.py"]

# 方法 2：如果 run.py 不可用，使用以下命令
# CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
