"""
S3 檔案操作工具模組
用於生產環境的檔案上傳、刪除和 URL 生成
"""
import boto3
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
import logging

from app.config import Config

logger = logging.getLogger(__name__)

# S3 客戶端（延遲初始化）
_s3_client: Optional[boto3.client] = None


def get_s3_client():
    """取得 S3 客戶端（單例模式）"""
    global _s3_client
    
    if _s3_client is None:
        try:
            # 如果使用 IAM Role（EC2），不需要提供 credentials
            if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
                _s3_client = boto3.client(
                    's3',
                    region_name=Config.AWS_REGION,
                    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
                )
            else:
                # 使用 IAM Role 或環境變數（EC2 環境）
                _s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
            
            logger.info(f"S3 客戶端初始化成功，Region: {Config.AWS_REGION}, Bucket: {Config.S3_BUCKET_NAME}")
        except NoCredentialsError:
            error_msg = "無法初始化 S3 客戶端：缺少 AWS 憑證。請設定 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY，或確保 EC2 實例已附加具有 S3 權限的 IAM Role。"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"S3 客戶端初始化失敗：{str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    return _s3_client


def upload_file_to_s3(
    file_content: bytes,
    file_type: str,
    filename: str,
    content_type: Optional[str] = None,
    cache_control: Optional[str] = None
) -> str:
    """
    上傳檔案到 S3
    
    Args:
        file_content: 檔案內容（bytes）
        file_type: 'product' 或 'carousel'
        filename: 檔案名稱（不含路徑）
        content_type: MIME 類型（選填，會自動推斷）
        cache_control: Cache-Control header（選填，預設為 'public, max-age=3600, must-revalidate'）
                       對於可能被覆蓋的檔案，建議使用 'no-cache, must-revalidate'
    
    Returns:
        相對路徑（例如：products/abc123.jpg），用於儲存在資料庫
    """
    if not Config.S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME 未設定")
    
    # 構建 S3 Key（路徑）
    s3_key = f"uploads/{file_type}s/{filename}"
    
    # 自動推斷 content_type
    if not content_type:
        file_ext = Path(filename).suffix.lower()
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        content_type = content_type_map.get(file_ext, 'application/octet-stream')
    
    try:
        s3_client = get_s3_client()
        
        # 設定 Cache-Control headers（如果未指定，使用預設值）
        if cache_control is None:
            cache_control = 'public, max-age=3600, must-revalidate'
        
        # 上傳檔案
        s3_client.put_object(
            Bucket=Config.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            CacheControl=cache_control,
            # 設定公開讀取（如果需要）
            # ACL='public-read'  # 如果 Bucket Policy 允許
        )
        
        # 驗證檔案已成功上傳
        try:
            s3_client.head_object(Bucket=Config.S3_BUCKET_NAME, Key=s3_key)
            logger.info(f"檔案上傳成功並驗證：{s3_key}")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"檔案上傳後驗證失敗：檔案不存在 {s3_key}")
            else:
                logger.warning(f"無法驗證上傳的檔案：{str(e)}，但上傳操作已執行")
        
        # 返回相對路徑（用於儲存在資料庫）
        # 例如：products/abc123.jpg
        relative_path = f"{file_type}s/{filename}"
        return relative_path
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 上傳失敗 [錯誤代碼: {error_code}]：{error_message}")
        
        # 提供更友好的錯誤訊息
        if error_code == 'AccessDenied':
            raise ValueError(f"S3 上傳失敗：權限不足。請檢查 IAM 角色或 AWS 憑證是否具有 S3 寫入權限。")
        elif error_code == 'NoSuchBucket':
            raise ValueError(f"S3 上傳失敗：Bucket '{Config.S3_BUCKET_NAME}' 不存在。請檢查 S3_BUCKET_NAME 設定。")
        elif error_code == 'InvalidAccessKeyId':
            raise ValueError(f"S3 上傳失敗：AWS 存取金鑰無效。請檢查 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY 設定。")
        else:
            raise ValueError(f"S3 上傳失敗 [{error_code}]：{error_message}")
    except ValueError as e:
        # 重新拋出 ValueError（例如 S3_BUCKET_NAME 未設定或驗證失敗）
        raise
    except Exception as e:
        logger.error(f"上傳檔案時發生錯誤：{str(e)}", exc_info=True)
        raise ValueError(f"檔案上傳失敗：{str(e)}")


def delete_file_from_s3(relative_path: str) -> bool:
    """
    從 S3 刪除檔案
    
    Args:
        relative_path: 相對路徑（例如：products/abc123.jpg）
    
    Returns:
        是否成功刪除
    """
    if not Config.S3_BUCKET_NAME:
        logger.warning("S3_BUCKET_NAME 未設定，無法刪除檔案")
        return False
    
    # 構建 S3 Key
    s3_key = f"uploads/{relative_path}"
    
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=Config.S3_BUCKET_NAME,
            Key=s3_key
        )
        logger.info(f"檔案刪除成功：{s3_key}")
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            logger.warning(f"檔案不存在：{s3_key}")
            return False
        logger.error(f"S3 刪除失敗：{str(e)}")
        return False
    except Exception as e:
        logger.error(f"刪除檔案時發生錯誤：{str(e)}")
        return False


def get_s3_url(relative_path: str, version: Optional[str] = None) -> str:
    """
    取得 S3 檔案的公開 URL
    
    Args:
        relative_path: 相對路徑（例如：products/abc123.jpg 或 uploads/products/abc123.jpg）
        version: 版本號（選填，用於強制刷新 CDN 快取，例如時間戳或 updated_at）
    
    Returns:
        完整的 S3 URL（如果提供了 version，會在 URL 後面加上 ?v=version）
    """
    if not relative_path:
        logger.warning("get_s3_url: relative_path 為空")
        return ""
    
    # 標準化路徑：移除開頭的斜線和 uploads/ 前綴（如果存在）
    normalized_path = relative_path.lstrip('/')
    if normalized_path.startswith('uploads/'):
        normalized_path = normalized_path[8:]  # 移除 'uploads/' 前綴
    
    # 如果設定了自訂的 S3_BASE_URL（例如 CloudFront URL）
    if Config.S3_BASE_URL:
        # 移除尾部的斜線
        base_url = Config.S3_BASE_URL.rstrip('/')
        url = f"{base_url}/uploads/{normalized_path}"
        
        # 如果提供了版本號，加到 URL 後面以強制刷新 CDN 快取
        if version:
            # 將版本號轉換為查詢參數（使用時間戳格式）
            if isinstance(version, datetime):
                version_str = str(int(version.timestamp()))
            else:
                version_str = str(version)
            url = f"{url}?v={version_str}"
        
        logger.debug(f"get_s3_url: 使用 S3_BASE_URL，輸入: {relative_path}, 版本: {version}, 輸出: {url}")
        return url
    
    # 否則使用標準 S3 URL
    if not Config.S3_BUCKET_NAME:
        logger.warning("S3_BUCKET_NAME 未設定，無法生成 URL")
        return ""
    
    # 標準 S3 URL 格式
    # https://bucket-name.s3.region.amazonaws.com/uploads/products/abc123.jpg
    url = f"https://{Config.S3_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/uploads/{normalized_path}"
    
    # 如果提供了版本號，加到 URL 後面
    if version:
        if isinstance(version, datetime):
            version_str = str(int(version.timestamp()))
        else:
            version_str = str(version)
        url = f"{url}?v={version_str}"
    
    logger.debug(f"get_s3_url: 輸入: {relative_path}, 標準化: {normalized_path}, 版本: {version}, 輸出: {url}")
    return url


def rename_file_in_s3(old_relative_path: str, new_filename: str) -> str:
    """
    在 S3 中重命名檔案（實際上是複製後刪除）
    
    Args:
        old_relative_path: 舊檔案的相對路徑（例如：products/abc123.jpg）
        new_filename: 新檔案名稱（不含路徑，例如：1.jpg）
    
    Returns:
        新檔案的相對路徑（例如：products/1.jpg）
    
    Raises:
        ValueError: 如果重命名失敗
    """
    if not Config.S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME 未設定")
    
    # 取得檔案類型（products 或 carousels）
    file_type = old_relative_path.split('/')[0].rstrip('s')  # products -> product
    
    # 構建新的相對路徑
    new_relative_path = f"{file_type}s/{new_filename}"
    
    old_s3_key = f"uploads/{old_relative_path}"
    new_s3_key = f"uploads/{new_relative_path}"
    
    try:
        s3_client = get_s3_client()
        
        # 先檢查舊檔案是否存在
        try:
            s3_client.head_object(Bucket=Config.S3_BUCKET_NAME, Key=old_s3_key)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"原始檔案不存在：{old_s3_key}")
            else:
                raise
        
        # 複製物件（S3 沒有真正的重命名，需要複製後刪除）
        copy_source = {
            'Bucket': Config.S3_BUCKET_NAME,
            'Key': old_s3_key
        }
        
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=Config.S3_BUCKET_NAME,
            Key=new_s3_key
        )
        
        # 驗證新檔案已成功複製
        try:
            s3_client.head_object(Bucket=Config.S3_BUCKET_NAME, Key=new_s3_key)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"複製失敗：新檔案不存在 {new_s3_key}")
            else:
                raise
        
        # 刪除舊物件
        s3_client.delete_object(
            Bucket=Config.S3_BUCKET_NAME,
            Key=old_s3_key
        )
        
        logger.info(f"S3 檔案重命名成功：{old_s3_key} -> {new_s3_key}")
        return new_relative_path
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        error_msg = f"S3 重命名失敗 [{error_code}]：{error_message}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except ValueError:
        # 重新拋出 ValueError
        raise
    except Exception as e:
        error_msg = f"重命名檔案時發生錯誤：{str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)
