from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List
from app.models.cms import Carousel, StoreInfo
from app.utils.validators import CarouselCreate, StoreInfoUpdate
from app.utils.file_utils import delete_file
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_carousels(db: Session, store_id: int, is_active: bool = True) -> List[dict]:
    """取得輪播圖列表"""
    query = db.query(Carousel).filter(Carousel.store_id == store_id)
    
    if is_active:
        query = query.filter(Carousel.is_active == True)
    
    carousels = query.order_by(Carousel.display_order.asc(), Carousel.id.asc()).all()
    
    return [
        {
            "id": carousel.id,
            "title": carousel.title,
            "image_url": carousel.image_url,
            "link_url": carousel.link_url,
            "display_order": carousel.display_order,
            "is_active": carousel.is_active,
            "created_at": carousel.created_at.isoformat() if carousel.created_at else None,
            "updated_at": carousel.updated_at  # 保留 datetime 物件，用於版本號
        }
        for carousel in carousels
    ]


def create_carousel(db: Session, store_id: int, carousel_data: CarouselCreate) -> dict:
    """建立輪播圖"""
    # 檢查 display_order 是否重複（如果提供了 display_order）
    if carousel_data.display_order is not None:
        existing_carousel = db.query(Carousel).filter(
            Carousel.display_order == carousel_data.display_order,
            Carousel.store_id == store_id
        ).first()
        if existing_carousel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"顯示順序 {carousel_data.display_order} 已被使用"
            )
    
    new_carousel = Carousel(
        store_id=store_id,
        title=carousel_data.title,
        image_url=carousel_data.image_url,
        link_url=carousel_data.link_url,
        display_order=carousel_data.display_order,
        is_active=carousel_data.is_active
    )
    
    db.add(new_carousel)
    db.commit()
    db.refresh(new_carousel)
    
    logger.info(f"建立輪播圖成功：{new_carousel.id}")
    
    return {
        "id": new_carousel.id,
        "title": new_carousel.title,
        "image_url": new_carousel.image_url,
        "link_url": new_carousel.link_url,
        "display_order": new_carousel.display_order,
        "is_active": new_carousel.is_active,
        "created_at": new_carousel.created_at.isoformat() if new_carousel.created_at else None,
        "updated_at": new_carousel.updated_at  # 保留 datetime 物件，用於版本號
    }


def update_carousel(db: Session, store_id: int, carousel_id: int, update_dict: dict) -> dict:
    """更新輪播圖（支援部分更新）"""
    carousel = db.query(Carousel).filter(
        Carousel.id == carousel_id,
        Carousel.store_id == store_id
    ).first()
    
    if not carousel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="輪播圖不存在"
        )
    
    # 白名單：只允許更新這些欄位（明確排除 image_url）
    allowed_fields = {'title', 'link_url', 'display_order', 'is_active'}
    fields_to_update = {k: v for k, v in update_dict.items() if k in allowed_fields}
    
    # 檢查 display_order 是否重複
    if "display_order" in fields_to_update and fields_to_update["display_order"] is not None:
        existing = db.query(Carousel).filter(
            Carousel.display_order == fields_to_update["display_order"],
            Carousel.store_id == store_id,
            Carousel.id != carousel_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"顯示順序 {fields_to_update['display_order']} 已被使用"
            )
    
    # 使用 setattr 更新物件屬性（只更新允許的欄位）
    if fields_to_update:
        for field, value in fields_to_update.items():
            setattr(carousel, field, value)
        # updated_at 會由模型的 onupdate 自動處理
        db.commit()
        db.refresh(carousel)
    
    logger.info(f"更新輪播圖成功：{carousel_id}")
    
    return {
        "id": carousel.id,
        "title": carousel.title,
        "image_url": carousel.image_url,
        "link_url": carousel.link_url,
        "display_order": carousel.display_order,
        "is_active": carousel.is_active,
        "updated_at": carousel.updated_at  # 保留 datetime 物件，用於版本號
    }


def get_carousel_by_id(db: Session, store_id: int, carousel_id: int):
    """取得單一輪播圖"""
    return db.query(Carousel).filter(Carousel.id == carousel_id, Carousel.store_id == store_id).first()


def delete_carousel(db: Session, store_id: int, carousel_id: int) -> dict:
    """刪除輪播圖"""
    carousel = db.query(Carousel).filter(Carousel.id == carousel_id, Carousel.store_id == store_id).first()
    
    if not carousel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="輪播圖不存在"
        )
    
    # 刪除圖片檔案
    if carousel.image_url:
        delete_file(carousel.image_url)
    
    db.delete(carousel)
    db.commit()
    
    logger.info(f"刪除輪播圖成功：{carousel_id}")
    
    return {"message": "輪播圖已刪除"}


def get_store_info(db: Session, store_id: int) -> dict:
    """取得商店資訊"""
    store_info = db.query(StoreInfo).filter(StoreInfo.store_id == store_id).first()
    
    if not store_info:
        # 如果不存在，建立預設值
        store_info = StoreInfo(
            store_id=store_id,
            store_name="ShopFlow",
            store_description="歡迎來到 ShopFlow 購物平台"
        )
        db.add(store_info)
        db.commit()
        db.refresh(store_info)
    
    return {
        "id": store_info.id,
        "store_name": store_info.store_name,
        "store_description": store_info.store_description,
        "contact_email": store_info.contact_email,
        "contact_phone": store_info.contact_phone,
        "address": store_info.address,
        "business_hours": store_info.business_hours,
        "logo_url": store_info.logo_url,
        "favicon_url": store_info.favicon_url,
        "facebook_url": store_info.facebook_url,
        "instagram_url": store_info.instagram_url,
        "line_url": store_info.line_url,
        "updated_at": store_info.updated_at.isoformat() if store_info.updated_at else None
    }


def update_store_info(db: Session, store_id: int, store_data: StoreInfoUpdate) -> dict:
    """更新商店資訊"""
    store_info = db.query(StoreInfo).filter(StoreInfo.store_id == store_id).first()
    
    if not store_info:
        # 如果不存在，建立新的
        store_info = StoreInfo(store_id=store_id)
        db.add(store_info)
    
    # 如果更新 Logo，刪除舊 Logo
    old_logo_url = store_info.logo_url
    old_favicon_url = store_info.favicon_url
    
    update_data = store_data.dict(exclude_unset=True)
    
    if "logo_url" in update_data and update_data["logo_url"] != old_logo_url and old_logo_url:
        delete_file(old_logo_url)
    
    if "favicon_url" in update_data and update_data["favicon_url"] != old_favicon_url and old_favicon_url:
        delete_file(old_favicon_url)
    
    # 更新欄位
    for field, value in update_data.items():
        setattr(store_info, field, value)
    
    db.commit()
    db.refresh(store_info)
    
    logger.info("更新商店資訊成功")
    
    return get_store_info(db, store_id)
