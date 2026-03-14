from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app import get_db
from app.utils.auth_utils import get_current_admin
from app.utils.validators import (
    CategoryCreate, CategoryUpdate,
    ProductCreate, ProductUpdate,
    OrderUpdate,
    CarouselCreate,
    StoreInfoUpdate
)
from app.utils.file_utils import save_uploaded_file, save_uploaded_file_replace, delete_file, get_file_url, rename_file
from app.services import (
    # Product
    get_products as get_products_service,
    get_product_by_id,
    create_product,
    update_product,
    delete_product,
    # Order
    get_order_by_id,
    update_order_status,
    # CMS
    get_carousels,
    get_carousel_by_id,
    create_carousel,
    update_carousel,
    delete_carousel,
    get_store_info,
    update_store_info
)
from app.models.category import Category
from app.models.order import Order, OrderStatus
import logging

logger = logging.getLogger(__name__)

# 建立路由器
router = APIRouter()


# ==================== 認證相關 ====================

@router.post('/auth/login')
def admin_login(login_data: dict, db: Session = Depends(get_db)):
    """後台管理員登入（使用 services）"""
    from app.utils.validators import AdminLogin
    from app.services import authenticate_admin
    
    try:
        admin_login_data = AdminLogin(**login_data)
        return authenticate_admin(db, admin_login_data)
    except Exception as e:
        logger.error(f"管理員登入錯誤：{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登入失敗"
        )


# ==================== 分類管理 ====================

@router.post('/categories', response_model=dict, status_code=status.HTTP_201_CREATED)
def add_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """建立分類"""
    try:
        name = category_data.name
        
        # 檢查分類名稱是否已存在
        existing_category = db.query(Category).filter_by(name=name).first()
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該分類已存在"
            )
        
        # 檢查 sort_order 是否重複（如果提供了 sort_order）
        if category_data.sort_order is not None:
            existing_sort_order = db.query(Category).filter(
                Category.sort_order == category_data.sort_order
            ).first()
            if existing_sort_order:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"排序值 {category_data.sort_order} 已被使用"
                )

        # 建立新的分類物件並存入資料庫
        new_category = Category(
            name=name,
            sort_order=category_data.sort_order,
            is_active=category_data.is_active if category_data.is_active is not None else True
        )
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        
        logger.info(f"成功建立分類：{name}")

        return {
            "message": "分類建立成功",
            "category": {
                "id": new_category.id,
                "name": new_category.name,
                "sort_order": new_category.sort_order,
                "is_active": new_category.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"建立分類時發生錯誤：{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="伺服器內部錯誤"
        )


@router.get('/categories')
def get_categories(db: Session = Depends(get_db)):
    """取得所有分類（管理員端，包含所有分類）"""
    try:
        from sqlalchemy import func, case
        # 排序邏輯：
        # 1. 有 sort_order 值的分類排在前面，按 sort_order 由小到大排序
        # 2. sort_order 為 null 的分類排在後面，按 id 排序
        categories = db.query(Category)\
            .order_by(
                case((Category.sort_order.is_(None), 999999), else_=Category.sort_order).asc(),
                Category.id.asc()
            )\
            .all()
        categories_list = [
            {
                "id": category.id,
                "name": category.name,
                "sort_order": category.sort_order,
                "is_active": category.is_active
            }
            for category in categories
        ]

        logger.info(f"成功取得{len(categories_list)}個分類")

        return {
            "message": "取得分類成功",
            "categories": categories_list
        }
    
    except Exception as e:
        logger.error(f"取得分類時發生錯誤:{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="伺服器內部錯誤"
        )


@router.put('/categories/{category_id}')
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新分類"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分類不存在"
        )
    
    if category_data.name:
        # 檢查名稱是否已被其他分類使用
        existing = db.query(Category).filter(
            Category.name == category_data.name,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該分類名稱已被使用"
            )
        category.name = category_data.name
    
    # 更新 sort_order（如果提供）
    if category_data.sort_order is not None:
        # 檢查 sort_order 是否已被其他分類使用
        existing_sort_order = db.query(Category).filter(
            Category.sort_order == category_data.sort_order,
            Category.id != category_id
        ).first()
        if existing_sort_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"排序值 {category_data.sort_order} 已被使用"
            )
        category.sort_order = category_data.sort_order
    
    # 更新 is_active（如果提供）
    if category_data.is_active is not None:
        category.is_active = category_data.is_active
    
    db.commit()
    db.refresh(category)
    
    return {
        "message": "分類更新成功",
        "category": {
            "id": category.id,
            "name": category.name,
            "sort_order": category.sort_order,
            "is_active": category.is_active
        }
    }


@router.delete('/categories/{category_id}')
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """刪除分類"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分類不存在"
        )
    
    # 檢查是否有商品使用此分類
    if category.products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該分類下仍有商品，無法刪除"
        )
    
    db.delete(category)
    db.commit()
    
    return {"message": "分類已刪除"}


# ==================== 商品管理 ====================

@router.get('/products')
def get_products(
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "id",
    order: str = "desc",
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """取得商品列表"""
    result = get_products_service(
        db=db,
        category_id=category_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        order=order
    )
    
    # 處理圖片 URL
    for product in result["products"]:
        for img in product["images"]:
            original_path = img.get("image_url", "")
            img["image_url"] = get_file_url(original_path)
            if original_path and not img["image_url"]:
                logger.warning(f"商品 {product.get('id')} 圖片 URL 轉換失敗，原始路徑: {original_path}")
        
        # 處理 primary_image
        primary_image_path = product.get("primary_image")
        if primary_image_path:
            product["primary_image"] = get_file_url(primary_image_path)
            if not product["primary_image"]:
                logger.warning(f"商品 {product.get('id')} primary_image URL 轉換失敗，原始路徑: {primary_image_path}")
        # 為了向後兼容，也設置 image_url
        product["image_url"] = product.get("primary_image", "")
    
    return result


@router.get('/products/{product_id}')
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """取得商品詳情"""
    result = get_product_by_id(db, product_id, include_inactive=True)
    
    # 處理圖片 URL
    for img in result["images"]:
        img["image_url"] = get_file_url(img["image_url"])
    
    # 處理 primary_image URL
    if result.get("primary_image"):
        result["primary_image"] = get_file_url(result["primary_image"])
        # 為了向後兼容，也設置 image_url
        result["image_url"] = result["primary_image"]
    
    return result


@router.post('/products', status_code=status.HTTP_201_CREATED)
def create_product_route(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """建立商品"""
    try:
        return create_product(db, product_data)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"建立商品時發生錯誤：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立商品失敗：{str(e)}"
        )


@router.post('/products/{product_id}/images', status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """上傳商品圖片"""
    from app.models.product import Product, ProductImage
    
    # 檢查商品是否存在
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    # 檢查是否已經有主圖
    existing_primary = db.query(ProductImage).filter(
        ProductImage.product_id == product_id,
        ProductImage.is_primary == True
    ).first()
    
    # 決定是否設為主圖：
    # 1. 如果前端指定 is_primary=True，設為主圖（無論是否已有主圖）
    # 2. 如果前端指定 is_primary=False，不設為主圖（保持現有主圖）
    # 3. 如果前端指定 is_primary=True 且已有主圖，會移除舊主圖標記，設新圖為主圖
    final_is_primary = False
    if is_primary:
        # 如果前端明確指定設為主圖，設為主圖
        final_is_primary = True
        # 如果已有主圖，移除舊主圖標記
        if existing_primary:
            db.query(ProductImage).filter(
                ProductImage.product_id == product_id,
                ProductImage.is_primary == True
            ).update({"is_primary": False})
    
    # 保存圖片
    try:
        # 先保存文件（使用臨時名稱）
        temp_image_path = await save_uploaded_file(file, "product", prefix=f"product_{product_id}")
        
        # 建立圖片記錄（使用臨時路徑）
        new_image = ProductImage(
            product_id=product_id,
            image_url=temp_image_path,
            is_primary=final_is_primary,
            display_order=display_order
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        # 使用圖片 ID 重新命名文件
        from pathlib import Path
        file_ext = Path(file.filename).suffix.lower()
        new_filename = f"{new_image.id}{file_ext}"
        
        # 初始化最終路徑為臨時路徑（如果重命名失敗，使用臨時路徑）
        final_image_path = temp_image_path
        
        try:
            final_image_path = rename_file(temp_image_path, new_filename)
            
            # 如果重命名失敗（路徑沒有改變），記錄警告但不更新資料庫
            if final_image_path == temp_image_path:
                logger.warning(f"圖片重命名失敗，使用臨時路徑：{temp_image_path}")
                # 不更新資料庫，保持臨時路徑
            else:
                logger.info(f"圖片已重命名：{temp_image_path} -> {final_image_path}")
                # 更新資料庫中的路徑
                new_image.image_url = final_image_path
                db.commit()
                db.refresh(new_image)
        except ValueError as e:
            # S3 重命名失敗，但檔案已上傳，保持臨時路徑
            logger.error(f"圖片重命名失敗：{str(e)}，保持臨時路徑：{temp_image_path}")
            # 不更新資料庫，保持臨時路徑（檔案已存在於 S3）
            final_image_path = temp_image_path  # 確保使用臨時路徑
        
        return {
            "message": "圖片上傳成功",
            "image": {
                "id": new_image.id,
                "image_url": get_file_url(final_image_path),
                "is_primary": new_image.is_primary,
                "display_order": new_image.display_order
            }
        }
    except ValueError as e:
        # 檔案驗證或儲存相關的錯誤
        db.rollback()
        logger.error(f"上傳圖片錯誤（驗證/儲存）：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"圖片上傳失敗：{str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"上傳圖片錯誤：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上傳失敗：{str(e)}"
        )


class ProductImageUpdate(BaseModel):
    is_primary: Optional[bool] = None
    display_order: Optional[int] = None


@router.put('/products/{product_id}/images/{image_id}')
def update_product_image(
    product_id: int,
    image_id: int,
    image_data: ProductImageUpdate = Body(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新商品圖片資訊（設置為主圖、調整順序）"""
    from app.models.product import Product, ProductImage
    
    # 檢查商品是否存在
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    # 檢查圖片是否存在
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="圖片不存在"
        )
    
    # 如果設為主圖，將其他圖片的主圖標記移除
    if image_data.is_primary is True:
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == True,
            ProductImage.id != image_id
        ).update({"is_primary": False})
        image.is_primary = True
    elif image_data.is_primary is False:
        image.is_primary = False
    
    # 更新顯示順序
    if image_data.display_order is not None:
        image.display_order = image_data.display_order
    
    db.commit()
    db.refresh(image)
    
    return {
        "message": "圖片更新成功",
        "image": {
            "id": image.id,
            "image_url": get_file_url(image.image_url),
            "is_primary": image.is_primary,
            "display_order": image.display_order
        }
    }


@router.delete('/products/{product_id}/images/{image_id}')
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """刪除商品圖片"""
    from app.models.product import Product, ProductImage
    
    # 檢查商品是否存在
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    # 檢查圖片是否存在
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="圖片不存在"
        )
    
    # 刪除檔案
    image_path = image.image_url
    delete_file(image_path)
    
    # 刪除資料庫記錄
    db.delete(image)
    db.commit()
    
    return {"message": "圖片已刪除"}


@router.put('/products/{product_id}')
def update_product_route(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新商品"""
    return update_product(db, product_id, product_data)


@router.delete('/products/{product_id}')
def delete_product_route(
    product_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """刪除商品"""
    return delete_product(db, product_id)


# ==================== 訂單管理 ====================

@router.get('/orders')
def get_orders(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """取得訂單列表"""
    query = db.query(Order)
    
    if status:
        try:
            order_status = OrderStatus(status)
            query = query.filter(Order.status == order_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的訂單狀態：{status}"
            )
    
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    orders_list = []
    for order in orders:
        orders_list.append({
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": order.customer.name if order.customer else None,
            "status": order.status.value,
            "total": order.total,
            "payment_status": order.payment_status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "item_count": len(order.items)
        })
    
    return {
        "orders": orders_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get('/orders/{order_id}')
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """取得訂單詳情"""
    return get_order_by_id(db, order_id)


@router.put('/orders/{order_id}')
def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新訂單狀態"""
    return update_order_status(db, order_id, order_data)


# ==================== CMS 管理 ====================

@router.get('/carousels')
def get_carousels_route(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """取得輪播圖列表"""
    carousels = get_carousels(db, is_active=is_active if is_active is not None else True)
    # 轉換 image_url 為完整的 URL 路徑，使用 updated_at 作為版本號以強制刷新 CDN 快取
    for carousel in carousels:
        updated_at = carousel.get("updated_at")
        carousel["image_url"] = get_file_url(carousel["image_url"], version=updated_at)
        # 將 updated_at 轉換為 ISO 格式字串以便 JSON 序列化
        if updated_at:
            carousel["updated_at"] = updated_at.isoformat() if hasattr(updated_at, 'isoformat') else str(updated_at)
    return carousels


@router.post('/carousels', status_code=status.HTTP_201_CREATED)
async def create_carousel_route(
    title: Optional[str] = Form(None),
    image: UploadFile = File(...),
    link_url: Optional[str] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """建立輪播圖"""
    try:
        # 上傳圖片
        image_path = await save_uploaded_file(image, "carousel")
        
        # 建立輪播圖
        carousel_data = CarouselCreate(
            title=title,
            image_url=image_path,
            link_url=link_url,
            display_order=display_order,
            is_active=is_active
        )
        
        result = create_carousel(db, carousel_data)
        # 使用 updated_at 作為版本號以強制刷新 CDN 快取
        updated_at = result.get("updated_at")
        result["image_url"] = get_file_url(result["image_url"], version=updated_at)
        # 將 updated_at 轉換為 ISO 格式字串以便 JSON 序列化
        if updated_at:
            result["updated_at"] = updated_at.isoformat() if hasattr(updated_at, 'isoformat') else str(updated_at)
        return result
    except Exception as e:
        logger.error(f"建立輪播圖錯誤：{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立失敗：{str(e)}"
        )


@router.put('/carousels/{carousel_id}')
async def update_carousel_route(
    carousel_id: int,
    title: Optional[str] = Form(None),
    link_url: Optional[str] = Form(None),
    display_order: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新輪播圖（支援更新 title, link_url, display_order, is_active 和圖片）
    
    如果提供圖片，會更新圖片；如果沒有提供圖片，則不更新圖片。
    """
    try:
        # 先取得輪播圖（用於檢查是否存在和處理圖片）
        carousel = get_carousel_by_id(db, carousel_id)
        if not carousel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="輪播圖不存在"
            )
        
        # 處理圖片更新（如果提供了圖片）
        if image is not None:
            if carousel.image_url:
                # 如果有舊圖片，覆蓋舊圖片
                await save_uploaded_file_replace(image, carousel.image_url)
            else:
                # 如果沒有舊圖片，建立新圖片
                image_path = await save_uploaded_file(image, "carousel")
                carousel.image_url = image_path
                db.commit()
                db.refresh(carousel)
        
        display_order_int = None
        if display_order is not None:
            try:
                display_order_int = int(display_order)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"無效的 display_order 值：{display_order}"
                )
        
        is_active_bool = None
        if is_active is not None:
            is_active_lower = is_active.lower()
            if is_active_lower in ('true', '1', 'yes'):
                is_active_bool = True
            elif is_active_lower in ('false', '0', 'no'):
                is_active_bool = False
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"無效的 is_active 值：{is_active}，應為 true 或 false"
                )
        
        update_dict = {}
        if title is not None:
            update_dict['title'] = title.strip() if isinstance(title, str) else title
        if link_url is not None:
            update_dict['link_url'] = link_url.strip() if isinstance(link_url, str) else link_url
        
        if display_order_int is not None:
            update_dict['display_order'] = display_order_int
        
        if is_active_bool is not None:
            update_dict['is_active'] = is_active_bool
        
        # 如果沒有提供任何要更新的欄位（包括圖片），則報錯
        if not update_dict and image is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供一個要更新的欄位"
            )
        
        # 更新其他欄位
        if update_dict:
            result = update_carousel(db, carousel_id, update_dict)
        else:
            # 如果只更新圖片，沒有更新其他欄位，重新整理 carousel 以取得最新資料
            db.refresh(carousel)
            result = {
                "id": carousel.id,
                "title": carousel.title,
                "image_url": carousel.image_url,
                "link_url": carousel.link_url,
                "display_order": carousel.display_order,
                "is_active": carousel.is_active,
                "updated_at": carousel.updated_at  # 保留 datetime 物件，用於版本號
            }
        
        # 確保返回最新的 image_url，使用 updated_at 作為版本號以強制刷新 CDN 快取
        if result.get("image_url"):
            updated_at = result.get("updated_at")
            result["image_url"] = get_file_url(result["image_url"], version=updated_at)
        # 將 updated_at 轉換為 ISO 格式字串以便 JSON 序列化
        if result.get("updated_at"):
            updated_at = result["updated_at"]
            result["updated_at"] = updated_at.isoformat() if hasattr(updated_at, 'isoformat') else str(updated_at)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新輪播圖錯誤：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失敗：{str(e)}"
        )


@router.put('/carousels/{carousel_id}/image')
async def update_carousel_image_route(
    carousel_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新輪播圖圖片
    
    機制：將新圖片以舊圖片相同檔名覆蓋保存，資料庫 image_url 不變
    """
    carousel = get_carousel_by_id(db, carousel_id)
    if not carousel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="輪播圖不存在"
        )
    if not carousel.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該輪播圖沒有圖片，請先建立輪播圖時上傳圖片"
        )
    try:
        await save_uploaded_file_replace(image, carousel.image_url)
        # 手動更新 updated_at 以觸發版本號變更
        from datetime import datetime
        carousel.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(carousel)
        
        result = {
            "id": carousel.id,
            "image_url": get_file_url(carousel.image_url, version=carousel.updated_at),
            "message": "圖片已更新"
        }
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新輪播圖圖片錯誤：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新圖片失敗：{str(e)}"
        )


@router.delete('/carousels/{carousel_id}')
def delete_carousel_route(
    carousel_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """刪除輪播圖"""
    return delete_carousel(db, carousel_id)


@router.get('/store-info')
def get_store_info_route(db: Session = Depends(get_db)):
    """取得商店資訊"""
    result = get_store_info(db)
    if result.get("logo_url"):
        result["logo_url"] = get_file_url(result["logo_url"])
    if result.get("favicon_url"):
        result["favicon_url"] = get_file_url(result["favicon_url"])
    return result


@router.put('/store-info')
def update_store_info_route(
    store_data: StoreInfoUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新商店資訊"""
    result = update_store_info(db, store_data)
    if result.get("logo_url"):
        result["logo_url"] = get_file_url(result["logo_url"])
    if result.get("favicon_url"):
        result["favicon_url"] = get_file_url(result["favicon_url"])
    return result
