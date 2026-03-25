from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app import get_db
from app.utils.dependencies import get_store, get_current_store_customer
from app.utils.validators import (
    CustomerRegister, CustomerLogin,
    OrderCreate,
    CartItemCreate, CartItemUpdate, CartItemBatchCreate
)
from app.services import (
    # Auth
    register_customer,
    authenticate_customer,
    # Product
    get_products as get_products_service,
    get_product_by_id,
    search_products,
    # Cart
    get_or_create_cart,
    add_to_cart,
    add_to_cart_batch,
    update_cart_item,
    remove_from_cart,
    clear_cart,
    get_cart_details,
    # Order
    create_order,
    get_orders_by_customer,
    get_order_by_id,
    cancel_order,
    # CMS
    get_carousels,
    get_store_info
)
from app.utils.file_utils import get_file_url
from app.models.category import Category
import logging

logger = logging.getLogger(__name__)

# 建立路由器
router = APIRouter()


# ==================== 認證相關 ====================

@router.post('/auth/register', status_code=status.HTTP_201_CREATED)
def register(customer_data: CustomerRegister, store = Depends(get_store), db: Session = Depends(get_db)):
    """客戶註冊"""
    try:
        return register_customer(db, store.id, customer_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"註冊錯誤：{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="註冊失敗"
        )


@router.post('/auth/login')
def login(login_data: CustomerLogin, store = Depends(get_store), db: Session = Depends(get_db)):
    """客戶登入"""
    try:
        return authenticate_customer(db, store.id, login_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登入錯誤：{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登入失敗"
        )


@router.get('/auth/me')
def get_current_customer_info(
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """取得當前登入客戶資訊"""
    return {
        "id": customer.id,
        "email": customer.email,
        "name": customer.name,
        "phone": customer.phone,
        "address": customer.address
    }


# ==================== 分類相關 ====================

@router.get('/categories')
def get_categories(store = Depends(get_store), db: Session = Depends(get_db)):
    """取得所有分類（僅顯示生效的分類，並依照排序顯示）"""
    try:
        # 只取得 is_active=True 的分類
        # 排序邏輯：
        # 1. 有 sort_order 值的分類排在前面，按 sort_order 由小到大排序
        # 2. sort_order 為 null 的分類排在後面，按 id 排序
        from sqlalchemy import func, case
        categories = db.query(Category)\
            .filter(Category.store_id == store.id)\
            .filter(Category.is_active == True)\
            .order_by(
                case((Category.sort_order.is_(None), 999999), else_=Category.sort_order).asc(),
                Category.id.asc()
            )\
            .all()
        
        categories_list = [
            {
                "id": category.id,
                "name": category.name,
                "sort_order": category.sort_order
            }
            for category in categories
        ]

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


# ==================== 商品相關 ====================

@router.get('/products')
def get_products(
    store = Depends(get_store),
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "id",
    order: str = "desc",
    db: Session = Depends(get_db)
):
    """取得商品列表（僅顯示啟用商品）"""
    result = get_products_service(
        db=db,
        store_id=store.id,
        category_id=category_id,
        is_active=True,  # 前台只顯示啟用商品
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        order=order
    )
    
    # 處理圖片 URL
    for product in result["products"]:
        for img in product["images"]:
            img["image_url"] = get_file_url(img["image_url"])
        if product.get("primary_image"):
            product["primary_image"] = get_file_url(product["primary_image"])
    
    return result


@router.get('/products/search')
def search_products_route(
    keyword: str,
    store = Depends(get_store),
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "id",
    order: str = "desc",
    db: Session = Depends(get_db)
):
    """搜尋商品"""
    result = search_products(
        db=db,
        store_id=store.id,
        keyword=keyword,
        category_id=category_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        order=order
    )
    
    # 處理圖片 URL
    for product in result["products"]:
        if product.get("primary_image"):
            product["primary_image"] = get_file_url(product["primary_image"])
    
    return result


@router.get('/products/{product_id}')
def get_product(product_id: int, store = Depends(get_store), db: Session = Depends(get_db)):
    """取得商品詳情"""
    result = get_product_by_id(db, store.id, product_id, include_inactive=False)
    
    # 處理圖片 URL
    for img in result["images"]:
        img["image_url"] = get_file_url(img["image_url"])
    
    # 處理 primary_image URL
    if result.get("primary_image"):
        result["primary_image"] = get_file_url(result["primary_image"])
    
    return result


# ==================== 購物車相關 ====================

@router.get('/cart')
def get_cart(
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """取得購物車"""
    cart = get_or_create_cart(db, customer.store_id, customer.id)
    result = get_cart_details(db, customer.store_id, cart.id)
    
    # 處理圖片 URL
    for item in result["items"]:
        if item.get("primary_image"):
            item["primary_image"] = get_file_url(item["primary_image"])
    
    return result


@router.post('/cart/items/batch', status_code=status.HTTP_201_CREATED)
def add_items_to_cart_batch(
    batch_data: CartItemBatchCreate,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """批次添加商品到購物車（可一次加入多個商品／多個規格與數量）"""
    result = add_to_cart_batch(db, customer.store_id, customer.id, batch_data)
    for item in result["items"]:
        if item.get("primary_image"):
            item["primary_image"] = get_file_url(item["primary_image"])
    return result


@router.post('/cart/items', status_code=status.HTTP_201_CREATED)
def add_item_to_cart(
    item_data: CartItemCreate,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """添加單一商品到購物車"""
    result = add_to_cart(db, customer.store_id, customer.id, item_data)
    for item in result["items"]:
        if item.get("primary_image"):
            item["primary_image"] = get_file_url(item["primary_image"])
    return result


@router.put('/cart/items/{item_id}')
def update_cart_item_route(
    item_id: int,
    item_data: CartItemUpdate,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """更新購物車項目數量"""
    result = update_cart_item(db, customer.store_id, customer.id, item_id, item_data)
    
    # 處理圖片 URL
    for item in result["items"]:
        if item.get("primary_image"):
            item["primary_image"] = get_file_url(item["primary_image"])
    
    return result


@router.delete('/cart/items/{item_id}')
def remove_item_from_cart(
    item_id: int,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """從購物車移除項目"""
    result = remove_from_cart(db, customer.store_id, customer.id, item_id)
    
    # 處理圖片 URL
    for item in result["items"]:
        if item.get("primary_image"):
            item["primary_image"] = get_file_url(item["primary_image"])
    
    return result


@router.delete('/cart')
def clear_cart_route(
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """清空購物車"""
    return clear_cart(db, customer.store_id, customer.id)


# ==================== 訂單相關 ====================

@router.post('/orders', status_code=status.HTTP_201_CREATED)
def create_order_route(
    order_data: OrderCreate,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """建立訂單"""
    return create_order(db, customer.store_id, customer.id, order_data)


@router.get('/orders')
def get_my_orders(
    skip: int = 0,
    limit: int = 20,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """取得我的訂單列表"""
    return get_orders_by_customer(db, customer.store_id, customer.id, skip, limit)


@router.get('/orders/{order_id}')
def get_my_order(
    order_id: int,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """取得訂單詳情"""
    return get_order_by_id(db, customer.store_id, order_id, customer_id=customer.id)


@router.post('/orders/{order_id}/cancel')
def cancel_my_order(
    order_id: int,
    customer = Depends(get_current_store_customer),
    db: Session = Depends(get_db)
):
    """取消訂單"""
    try:
        return cancel_order(db, customer.store_id, order_id, customer_id=customer.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消訂單失敗：{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消訂單失敗"
        )


# ==================== CMS 相關 ====================

@router.get('/carousels')
def get_carousels_route(store = Depends(get_store), db: Session = Depends(get_db)):
    """取得輪播圖列表（僅顯示啟用）"""
    carousels = get_carousels(db, store.id, is_active=True)
    
    # 處理圖片 URL，使用 updated_at 作為版本號以強制刷新 CDN 快取
    for carousel in carousels:
        updated_at = carousel.get("updated_at")
        carousel["image_url"] = get_file_url(carousel["image_url"], version=updated_at)
        # 將 updated_at 轉換為 ISO 格式字串以便 JSON 序列化
        if updated_at:
            carousel["updated_at"] = updated_at.isoformat() if hasattr(updated_at, 'isoformat') else str(updated_at)
    
    return {"carousels": carousels}


@router.get('/store-info')
def get_store_info_route(store = Depends(get_store), db: Session = Depends(get_db)):
    """取得商店資訊"""
    result = get_store_info(db, store.id)
    
    # 處理圖片 URL
    if result.get("logo_url"):
        result["logo_url"] = get_file_url(result["logo_url"])
    if result.get("favicon_url"):
        result["favicon_url"] = get_file_url(result["favicon_url"])
    
    return result
