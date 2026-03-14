import os
import uuid
from fastapi import UploadFile
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys
import logging

# 導入 config (從 app 包導入)
from app.config import Config

logger = logging.getLogger(__name__)

# 取得 app 目錄（app/utils/file_utils.py -> app/）
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 上傳檔案基礎路徑（僅用於本地儲存模式）
UPLOAD_BASE_DIR = os.path.join(basedir, "static", "uploads")
PRODUCTS_UPLOAD_DIR = os.path.join(UPLOAD_BASE_DIR, "products")
CAROUSELS_UPLOAD_DIR = os.path.join(UPLOAD_BASE_DIR, "carousels")

# 允許的圖片格式
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def ensure_upload_directories():
    """確保上傳目錄存在"""
    os.makedirs(PRODUCTS_UPLOAD_DIR, exist_ok=True)
    os.makedirs(CAROUSELS_UPLOAD_DIR, exist_ok=True)


def get_upload_path(file_type: str) -> str:
    """取得上傳路徑
    
    Args:
        file_type: 'product' 或 'carousel'
    
    Returns:
        上傳目錄路徑
    """
    if file_type == "product":
        return PRODUCTS_UPLOAD_DIR
    elif file_type == "carousel":
        return CAROUSELS_UPLOAD_DIR
    else:
        raise ValueError(f"不支援的檔案類型: {file_type}")


def validate_image_file(file: UploadFile) -> tuple[bool, str]:
    """驗證圖片檔案
    
    Returns:
        (is_valid, error_message)
    """
    # 檢查檔案名稱是否存在
    if not file.filename:
        return False, "檔案名稱不能為空"
    
    # 檢查檔案擴展名
    try:
        file_ext = Path(file.filename).suffix.lower()
        if not file_ext:
            return False, f"檔案必須有副檔名。允許的格式：{', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, f"不支援的檔案格式：{file_ext}。允許的格式：{', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
    except Exception as e:
        return False, f"無法解析檔案名稱：{str(e)}"
    
    # 檢查檔案大小（需要讀取檔案內容）
    # 注意：這裡只檢查檔案名稱，實際大小檢查在保存時進行
    return True, ""


async def save_uploaded_file(
    file: UploadFile,
    file_type: str,
    prefix: str = ""
) -> str:
    """保存上傳的檔案（根據環境自動選擇本地或 S3）
    
    Args:
        file: FastAPI UploadFile 物件
        file_type: 'product' 或 'carousel'
        prefix: 檔案名稱前綴（選填）
    
    Returns:
        相對於 static/uploads 的路徑（用於儲存在資料庫）
        例如：products/abc123.jpg
    """
    # 驗證檔案
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise ValueError(error_msg)
    
    # 讀取檔案內容
    contents = await file.read()
    
    # 檢查檔案大小
    if len(contents) > MAX_FILE_SIZE:
        raise ValueError(f"檔案大小超過限制（最大 {MAX_FILE_SIZE / 1024 / 1024}MB）")
    
    # 生成唯一檔案名稱
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{prefix}_{uuid.uuid4().hex}{file_ext}" if prefix else f"{uuid.uuid4().hex}{file_ext}"
    
    # 根據儲存模式選擇上傳方式
    if Config.FILE_STORAGE_MODE == 's3':
        # 使用 S3 上傳
        try:
            from app.utils.s3_utils import upload_file_to_s3
            relative_path = upload_file_to_s3(
                file_content=contents,
                file_type=file_type,
                filename=unique_filename,
                content_type=file.content_type
            )
            logger.info(f"檔案已上傳到 S3：{relative_path}")
            return relative_path
        except ImportError:
            error_msg = "無法導入 s3_utils 模組"
            logger.error(error_msg)
            if Config.IS_PRODUCTION:
                # 生產環境不允許回退，直接拋出錯誤
                raise ValueError(f"{error_msg}。請檢查 S3 配置和依賴項。")
            else:
                # 開發環境允許回退到本地儲存
                logger.warning(f"{error_msg}，回退到本地儲存")
        except Exception as e:
            error_msg = f"S3 上傳失敗：{str(e)}"
            logger.error(error_msg, exc_info=True)
            if Config.IS_PRODUCTION:
                # 生產環境不允許回退，直接拋出錯誤
                raise ValueError(f"{error_msg}。請檢查 S3 配置、權限和網路連線。")
            else:
                # 開發環境允許回退到本地儲存
                logger.warning(f"{error_msg}，回退到本地儲存")
    
    # 本地儲存（開發環境或 S3 失敗時的回退）
    ensure_upload_directories()
    upload_dir = get_upload_path(file_type)
    file_path = os.path.join(upload_dir, unique_filename)
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # 返回相對路徑（用於儲存在資料庫）
        relative_path = os.path.join(file_type + "s", unique_filename).replace("\\", "/")
        logger.info(f"檔案已保存到本地：{relative_path}")
        return relative_path
    except Exception as e:
        logger.error(f"本地儲存失敗：{str(e)}", exc_info=True)
        raise ValueError(f"檔案儲存失敗：{str(e)}")


async def save_uploaded_file_replace(file: UploadFile, target_relative_path: str) -> str:
    """將上傳的檔案以指定路徑覆蓋保存（用於替換舊圖片，檔名與路徑不變）
    
    Args:
        file: FastAPI UploadFile 物件
        target_relative_path: 目標相對路徑（例如：carousels/abc123.jpg）
    
    Returns:
        相對路徑（與 target_relative_path 相同）
    """
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise ValueError(error_msg)
    
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValueError(f"檔案大小超過限制（最大 {MAX_FILE_SIZE / 1024 / 1024}MB）")
    
    # 根據儲存模式選擇上傳方式
    if Config.FILE_STORAGE_MODE == 's3':
        # 使用 S3 上傳（覆蓋）
        try:
            from app.utils.s3_utils import upload_file_to_s3
            
            # 從相對路徑提取檔案名稱
            filename = os.path.basename(target_relative_path)
            file_type = target_relative_path.split('/')[0].rstrip('s')  # products -> product
            
            upload_file_to_s3(
                file_content=contents,
                file_type=file_type,
                filename=filename,
                content_type=file.content_type,
                cache_control='no-cache, must-revalidate'  # 覆蓋檔案時不緩存，強制重新驗證
            )
            logger.info(f"檔案已覆蓋上傳到 S3：{target_relative_path}")
            return target_relative_path
        except ImportError:
            error_msg = "無法導入 s3_utils 模組"
            logger.error(error_msg)
            if Config.IS_PRODUCTION:
                raise ValueError(f"{error_msg}。請檢查 S3 配置和依賴項。")
            else:
                logger.warning(f"{error_msg}，回退到本地儲存")
        except Exception as e:
            error_msg = f"S3 上傳失敗：{str(e)}"
            logger.error(error_msg, exc_info=True)
            if Config.IS_PRODUCTION:
                raise ValueError(f"{error_msg}。請檢查 S3 配置、權限和網路連線。")
            else:
                logger.warning(f"{error_msg}，回退到本地儲存")
    
    # 本地儲存（開發環境或 S3 失敗時的回退）
    ensure_upload_directories()
    target_abs_path = os.path.join(UPLOAD_BASE_DIR, target_relative_path) if not os.path.isabs(target_relative_path) else target_relative_path
    target_dir = os.path.dirname(target_abs_path)
    os.makedirs(target_dir, exist_ok=True)
    
    # 直接覆蓋：使用與舊圖片相同的完整路徑與檔名
    with open(target_abs_path, "wb") as f:
        f.write(contents)
    
    logger.info(f"檔案已覆蓋保存到本地：{target_relative_path}")
    return target_relative_path


def rename_file(old_path: str, new_filename: str) -> str:
    """重命名檔案（根據環境自動選擇本地或 S3）
    
    Args:
        old_path: 舊檔案的相對路徑（例如：products/abc123.jpg）
        new_filename: 新檔案名稱（不含路徑，例如：1.jpg）
    
    Returns:
        新檔案的相對路徑（例如：products/1.jpg）
    """
    # 根據儲存模式選擇重命名方式
    if Config.FILE_STORAGE_MODE == 's3':
        try:
            from app.utils.s3_utils import rename_file_in_s3
            new_path = rename_file_in_s3(old_path, new_filename)
            logger.info(f"S3 檔案重命名：{old_path} -> {new_path}")
            return new_path
        except ImportError:
            error_msg = "無法導入 s3_utils 模組"
            logger.error(error_msg)
            if Config.IS_PRODUCTION:
                raise ValueError(f"{error_msg}。請檢查 S3 配置和依賴項。")
            else:
                logger.warning(f"{error_msg}，回退到本地重命名")
        except ValueError as e:
            # 重新拋出 ValueError（S3 重命名失敗）
            logger.error(f"S3 重命名失敗：{str(e)}")
            if Config.IS_PRODUCTION:
                raise  # 生產環境不允許回退
            else:
                logger.warning(f"S3 重命名失敗：{str(e)}，回退到本地重命名")
        except Exception as e:
            error_msg = f"S3 重命名失敗：{str(e)}"
            logger.error(error_msg, exc_info=True)
            if Config.IS_PRODUCTION:
                raise ValueError(error_msg)
            else:
                logger.warning(f"{error_msg}，回退到本地重命名")
    
    # 本地重命名（開發環境或 S3 失敗時的回退）
    try:
        # 轉換為絕對路徑
        if not os.path.isabs(old_path):
            old_abs_path = os.path.join(UPLOAD_BASE_DIR, old_path)
        else:
            old_abs_path = old_path
        
        # 取得檔案所在目錄
        file_dir = os.path.dirname(old_abs_path)
        
        # 構建新路徑
        new_abs_path = os.path.join(file_dir, new_filename)
        
        # 重命名檔案
        if os.path.exists(old_abs_path):
            os.rename(old_abs_path, new_abs_path)
            
            # 返回相對路徑
            relative_path = os.path.relpath(new_abs_path, UPLOAD_BASE_DIR).replace("\\", "/")
            logger.info(f"本地檔案重命名：{old_path} -> {relative_path}")
            return relative_path
        
        return old_path
    except Exception as e:
        logger.error(f"重命名檔案失敗：{str(e)}")
        # 如果重命名失敗，返回原路徑
        return old_path


def delete_file(file_path: str) -> bool:
    """刪除檔案（根據環境自動選擇本地或 S3）
    
    Args:
        file_path: 相對路徑（例如：products/abc123.jpg）或絕對路徑
    
    Returns:
        是否成功刪除
    """
    # 根據儲存模式選擇刪除方式
    if Config.FILE_STORAGE_MODE == 's3':
        try:
            from app.utils.s3_utils import delete_file_from_s3
            
            # 如果是絕對路徑，轉換為相對路徑
            if os.path.isabs(file_path):
                # 嘗試從絕對路徑提取相對路徑
                try:
                    file_path = os.path.relpath(file_path, UPLOAD_BASE_DIR).replace("\\", "/")
                except ValueError:
                    # 如果無法轉換，可能是 S3 路徑，直接使用
                    pass
            
            result = delete_file_from_s3(file_path)
            if result:
                logger.info(f"S3 檔案刪除成功：{file_path}")
            return result
        except ImportError:
            logger.error("無法導入 s3_utils，回退到本地刪除")
            pass
        except Exception as e:
            logger.error(f"S3 刪除失敗：{str(e)}，回退到本地刪除")
            pass
    
    # 本地刪除（開發環境或 S3 失敗時的回退）
    try:
        # 如果是相對路徑，轉換為絕對路徑
        if not os.path.isabs(file_path):
            file_path = os.path.join(UPLOAD_BASE_DIR, file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"本地檔案刪除成功：{file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"刪除檔案失敗：{str(e)}")
        return False


def get_file_url(file_path: str, version: Optional[str] = None) -> str:
    """取得檔案的 URL 路徑（根據環境自動選擇本地或 S3 URL）
    
    Args:
        file_path: 相對路徑（例如：products/abc123.jpg）
        version: 版本號（選填，用於強制刷新 CDN 快取，例如時間戳或 updated_at）
                 可以是 datetime 物件或字串
    
    Returns:
        URL 路徑
        - 本地模式：/static/uploads/products/abc123.jpg（如果提供 version，會加上 ?v=version）
        - S3 模式：https://bucket.s3.region.amazonaws.com/uploads/products/abc123.jpg（如果提供 version，會加上 ?v=version）
    """
    if not file_path:
        return ""
    
    # 根據儲存模式選擇 URL 生成方式
    if Config.FILE_STORAGE_MODE == 's3':
        try:
            from app.utils.s3_utils import get_s3_url
            url = get_s3_url(file_path, version=version)
            return url
        except ImportError:
            logger.warning("無法導入 s3_utils，使用本地 URL")
            pass
        except Exception as e:
            logger.warning(f"生成 S3 URL 失敗：{str(e)}，使用本地 URL")
            pass
    
    # 本地 URL（開發環境或 S3 失敗時的回退）
    url = f"/static/uploads/{file_path}"
    
    # 如果提供了版本號，加到 URL 後面
    if version:
        if isinstance(version, datetime):
            version_str = str(int(version.timestamp()))
        else:
            version_str = str(version)
        url = f"{url}?v={version_str}"
    
    return url
