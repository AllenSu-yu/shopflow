from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from fastapi import HTTPException, status
from typing import Optional, List
from app.models.product import Product, ProductImage, ProductSpecGroup, ProductSpecValue, ProductVariant
from app.models.category import Category
from app.utils.validators import ProductCreate, ProductUpdate
import logging

logger = logging.getLogger(__name__)


def get_products(
    db: Session,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "id",  # id, price, created_at
    order: str = "desc"  # asc, desc
) -> dict:
    """取得商品列表（支援分類篩選、排序）"""
    query = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.spec_groups).joinedload(ProductSpecGroup.spec_values),
        joinedload(Product.variants).joinedload(ProductVariant.spec_value_1),
        joinedload(Product.variants).joinedload(ProductVariant.spec_value_2)
    )
    
    # 分類篩選
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # 啟用狀態篩選
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    # 排序
    if sort_by == "price":
        # 價格排序改為使用 id（因為價格在變體中，無法直接排序）
        # 如果需要價格排序，需要在應用層處理
        order_by_col = Product.id
    elif sort_by == "created_at":
        # 如果 Product 有 created_at 欄位，使用它；否則使用 id
        order_by_col = Product.id
    else:  # 預設使用 id
        order_by_col = Product.id
    
    if order == "asc":
        query = query.order_by(order_by_col.asc())
    else:
        query = query.order_by(order_by_col.desc())
    
    # 分頁
    total = query.count()
    products = query.offset(skip).limit(limit).all()
    
    # 轉換為字典格式（包含關聯資料）
    products_list = []
    for product in products:
        # 計算變體庫存總和作為商品總庫存
        if product.variants:
            display_stock = sum(variant.stock for variant in product.variants)
        else:
            display_stock = product.stock  # 向後兼容
        
        # 構建規格組結構
        spec_groups_list = []
        for spec_group in sorted(product.spec_groups, key=lambda x: x.sort_order):
            spec_group_dict = {
                "id": spec_group.id,
                "name": spec_group.name,
                "sort_order": spec_group.sort_order,
                "values": [
                    {
                        "id": val.id,
                        "value": val.value,
                        "sort_order": val.sort_order
                    }
                    for val in sorted(spec_group.spec_values, key=lambda x: (x.sort_order, x.id))
                ]
            }
            spec_groups_list.append(spec_group_dict)
        
        # 構建變體列表並計算價格範圍
        variants_list = []
        prices = []
        for variant in product.variants:
            variant_dict = {
                "id": variant.id,
                "spec_value_1": variant.spec_value_1.value if variant.spec_value_1 else None,
                "spec_value_2": variant.spec_value_2.value if variant.spec_value_2 else None,
                "price": variant.price,
                "stock": variant.stock
            }
            variants_list.append(variant_dict)
            prices.append(variant.price)
        
        # 計算價格範圍（最低價和最高價）
        min_price = min(prices) if prices else 0.0
        max_price = max(prices) if prices else 0.0
        price_display = f"{min_price:.0f}" if min_price == max_price else f"{min_price:.0f} - {max_price:.0f}"
        
        # 取得主要圖片（優先使用 is_primary=True 的圖片，否則使用第一張）
        sorted_images = sorted(product.images, key=lambda x: (x.display_order, x.id))
        primary_image = next(
            (img.image_url for img in sorted_images if img.is_primary),
            sorted_images[0].image_url if sorted_images else None
        )
        
        product_dict = {
            "id": product.id,
            "name": product.name,
            "price_range": {
                "min": min_price,
                "max": max_price,
                "display": price_display
            },
            "stock": display_stock,  # 顯示的庫存（變體庫存總和）
            "description": product.description,
            "is_active": product.is_active,
            "category_id": product.category_id,
            "category_name": product.category.name if product.category else None,
            "spec_groups": spec_groups_list,
            "variants": variants_list,
            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url,
                    "is_primary": img.is_primary,
                    "display_order": img.display_order
                }
                for img in sorted_images
            ],
            "primary_image": primary_image
        }
        products_list.append(product_dict)
    
    return {
        "products": products_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }


def get_product_by_id(db: Session, product_id: int, include_inactive: bool = False) -> dict:
    """取得單一商品詳情"""
    query = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.spec_groups).joinedload(ProductSpecGroup.spec_values),
        joinedload(Product.variants).joinedload(ProductVariant.spec_value_1),
        joinedload(Product.variants).joinedload(ProductVariant.spec_value_2)
    ).filter(Product.id == product_id)
    
    if not include_inactive:
        query = query.filter(Product.is_active == True)
    
    product = query.first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    # 計算變體庫存總和作為商品總庫存
    if product.variants:
        display_stock = sum(variant.stock for variant in product.variants)
    else:
        display_stock = product.stock  # 向後兼容
    
    # 構建規格組結構
    spec_groups_list = []
    for spec_group in sorted(product.spec_groups, key=lambda x: x.sort_order):
        spec_group_dict = {
            "id": spec_group.id,
            "name": spec_group.name,
            "sort_order": spec_group.sort_order,
            "values": [
                {
                    "id": val.id,
                    "value": val.value,
                    "sort_order": val.sort_order
                }
                for val in sorted(spec_group.spec_values, key=lambda x: (x.sort_order, x.id))
            ]
        }
        spec_groups_list.append(spec_group_dict)
    
    # 構建變體列表並計算價格範圍
    variants_list = []
    prices = []
    for variant in product.variants:
        variant_dict = {
            "id": variant.id,
            "spec_value_1": variant.spec_value_1.value if variant.spec_value_1 else None,
            "spec_value_2": variant.spec_value_2.value if variant.spec_value_2 else None,
            "price": variant.price,
            "stock": variant.stock
        }
        variants_list.append(variant_dict)
        prices.append(variant.price)
    
    # 計算價格範圍（最低價和最高價）
    min_price = min(prices) if prices else 0.0
    max_price = max(prices) if prices else 0.0
    price_display = f"{min_price:.0f}" if min_price == max_price else f"{min_price:.0f} - {max_price:.0f}"
    
    # 取得主要圖片（優先使用 is_primary=True 的圖片，否則使用第一張）
    sorted_images = sorted(product.images, key=lambda x: (x.display_order, x.id))
    primary_image = next(
        (img.image_url for img in sorted_images if img.is_primary),
        sorted_images[0].image_url if sorted_images else None
    )
    
    return {
        "id": product.id,
        "name": product.name,
        "price_range": {
            "min": min_price,
            "max": max_price,
            "display": price_display
        },
        "stock": display_stock,  # 顯示的庫存（變體庫存總和）
        "description": product.description,
        "is_active": product.is_active,
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else None,
        "spec_groups": spec_groups_list,
        "variants": variants_list,
        "images": [
            {
                "id": img.id,
                "image_url": img.image_url,
                "is_primary": img.is_primary,
                "display_order": img.display_order
            }
            for img in sorted_images
        ],
        "primary_image": primary_image
    }


def search_products(
    db: Session,
    keyword: str,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20
) -> dict:
    """搜尋商品（根據名稱或描述）"""
    query = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.variants)
    ).filter(
        and_(
            Product.is_active == True,
            or_(
                Product.name.contains(keyword),
                Product.description.contains(keyword) if Product.description else False
            )
        )
    )
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    total = query.count()
    products = query.offset(skip).limit(limit).all()
    
    products_list = []
    for product in products:
        # 計算庫存（變體庫存總和）
        if product.variants:
            display_stock = sum(variant.stock for variant in product.variants)
            # 計算價格範圍
            prices = [variant.price for variant in product.variants]
            min_price = min(prices) if prices else 0.0
            max_price = max(prices) if prices else 0.0
            price_display = f"{min_price:.0f}" if min_price == max_price else f"{min_price:.0f} - {max_price:.0f}"
        else:
            display_stock = product.stock  # 向後兼容
            min_price = 0.0
            max_price = 0.0
            price_display = "0"
        
        products_list.append({
            "id": product.id,
            "name": product.name,
            "price_range": {
                "min": min_price,
                "max": max_price,
                "display": price_display
            },
            "stock": display_stock,  # 變體庫存總和
            "category_id": product.category_id,
            "category_name": product.category.name if product.category else None,
            "primary_image": next(
                (img.image_url for img in sorted(product.images, key=lambda x: (x.display_order, x.id)) if img.is_primary),
                product.images[0].image_url if product.images else None
            )
        })
    
    return {
        "products": products_list,
        "total": total,
        "skip": skip,
        "limit": limit,
        "keyword": keyword
    }


def create_product(db: Session, product_data: ProductCreate) -> dict:
    """建立新商品（支援單層和兩層規格）"""
    try:
        # 檢查分類是否存在
        category = db.query(Category).filter(Category.id == product_data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分類不存在"
            )
        
        # 計算變體庫存總和作為商品總庫存
        product_stock = sum(variant.stock for variant in product_data.variants)
        
        # 建立商品
        new_product = Product(
            name=product_data.name,
            stock=product_stock,  # 總庫存 = 變體庫存總和
            description=product_data.description,
            category_id=product_data.category_id,
            is_active=product_data.is_active
        )
        
        db.add(new_product)
        db.flush()  # 取得新商品的 ID
        
        # 建立商品圖片
        if product_data.images:
            for img_data in product_data.images:
                img = ProductImage(
                    product_id=new_product.id,
                    image_url=img_data.image_url,
                    is_primary=img_data.is_primary,
                    display_order=img_data.display_order
                )
                db.add(img)
        
        # 建立規格組和規格值
        spec_value_map = {}  # 用於後續建立變體時查找規格值ID
        for spec_group_data in product_data.spec_groups:
            spec_group = ProductSpecGroup(
                product_id=new_product.id,
                name=spec_group_data.name,
                sort_order=spec_group_data.sort_order
            )
            db.add(spec_group)
            db.flush()  # 取得規格組的 ID
            
            # 建立規格值
            spec_value_map[spec_group_data.sort_order] = {}
            for spec_value_data in spec_group_data.values:
                spec_value = ProductSpecValue(
                    spec_group_id=spec_group.id,
                    value=spec_value_data.value,
                    sort_order=spec_value_data.sort_order
                )
                db.add(spec_value)
                db.flush()  # 取得規格值的 ID
                spec_value_map[spec_group_data.sort_order][spec_value_data.value] = spec_value.id
        
        # 建立變體
        for variant_data in product_data.variants:
            # 查找第一層規格值ID
            spec_value_1_id = spec_value_map[1].get(variant_data.spec_value_1)
            if not spec_value_1_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"變體的第一層規格值 '{variant_data.spec_value_1}' 不在規格組中"
                )
            
            # 查找第二層規格值ID（如果存在）
            spec_value_2_id = None
            if variant_data.spec_value_2:
                if 2 not in spec_value_map:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="變體包含第二層規格值，但商品只有一個規格組"
                    )
                spec_value_2_id = spec_value_map[2].get(variant_data.spec_value_2)
                if not spec_value_2_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"變體的第二層規格值 '{variant_data.spec_value_2}' 不在規格組中"
                    )
            
            # 查找對應的規格組ID
            spec_group_1_id = None
            spec_group_2_id = None
            for spec_group in new_product.spec_groups:
                if spec_group.sort_order == 1:
                    spec_group_1_id = spec_group.id
                elif spec_group.sort_order == 2:
                    spec_group_2_id = spec_group.id
            
            variant = ProductVariant(
                product_id=new_product.id,
                spec_group_1_id=spec_group_1_id,
                spec_value_1_id=spec_value_1_id,
                spec_group_2_id=spec_group_2_id,
                spec_value_2_id=spec_value_2_id,
                price=variant_data.price,
                stock=variant_data.stock
            )
            db.add(variant)
        
        db.commit()
        db.refresh(new_product)
        
        logger.info(f"建立商品成功：{new_product.name}")
        
        return get_product_by_id(db, new_product.id, include_inactive=True)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"建立商品時發生錯誤：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立商品失敗：{str(e)}"
        )


def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> dict:
    """更新商品（stock 由變體庫存總和自動計算）
    支援更新基本資訊和規格組/變體
    """
    try:
        product = db.query(Product).options(
            joinedload(Product.spec_groups).joinedload(ProductSpecGroup.spec_values),
            joinedload(Product.variants)
        ).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        
        # 更新基本欄位（排除 stock, spec_groups, variants）
        update_data = product_data.dict(exclude_unset=True)
        # 移除 stock 欄位（如果存在），因為它不應該被直接更新
        update_data.pop('stock', None)
        # 直接從 Pydantic 對象獲取 spec_groups 和 variants（保持為對象）
        spec_groups_data = product_data.spec_groups if hasattr(product_data, 'spec_groups') and product_data.spec_groups is not None else None
        variants_data = product_data.variants if hasattr(product_data, 'variants') and product_data.variants is not None else None
        # 從 update_data 中移除，避免在基本欄位更新時處理
        update_data.pop('spec_groups', None)
        update_data.pop('variants', None)
        
        # 檢查 spec_groups 和 variants 是否同時提供
        if (spec_groups_data is not None) != (variants_data is not None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新商品時，spec_groups 和 variants 必須同時提供或同時不提供"
            )
        
        for field, value in update_data.items():
            setattr(product, field, value)
        
        # 如果更新了分類，檢查分類是否存在
        if "category_id" in update_data:
            category = db.query(Category).filter(Category.id == product.category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="分類不存在"
                )
        
        # 如果提供了規格組和變體，則完全替換現有的規格組和變體
        if spec_groups_data is not None and variants_data is not None:
            # 先刪除現有的變體（因為變體引用規格值）
            db.query(ProductVariant).filter(ProductVariant.product_id == product.id).delete()
            
            # 手動刪除規格值（因為級聯刪除在使用 delete() 時可能不會自動執行）
            # 先取得所有規格組ID
            existing_spec_groups = db.query(ProductSpecGroup).filter(ProductSpecGroup.product_id == product.id).all()
            spec_group_ids = [sg.id for sg in existing_spec_groups]
            
            if spec_group_ids:
                # 刪除所有規格值
                db.query(ProductSpecValue).filter(ProductSpecValue.spec_group_id.in_(spec_group_ids)).delete()
            
            # 刪除現有的規格組
            db.query(ProductSpecGroup).filter(ProductSpecGroup.product_id == product.id).delete()
            
            db.flush()  # 確保刪除操作完成
            
            # 建立新的規格組和規格值
            spec_value_map = {}  # 用於後續建立變體時查找規格值ID
            spec_group_map = {}  # 用於儲存規格組ID
            for spec_group_data in spec_groups_data:
                spec_group = ProductSpecGroup(
                    product_id=product.id,
                    name=spec_group_data.name,
                    sort_order=spec_group_data.sort_order
                )
                db.add(spec_group)
                db.flush()  # 取得規格組的 ID
                
                spec_group_map[spec_group_data.sort_order] = spec_group.id
                
                # 建立規格值
                spec_value_map[spec_group_data.sort_order] = {}
                for spec_value_data in spec_group_data.values:
                    spec_value = ProductSpecValue(
                        spec_group_id=spec_group.id,
                        value=spec_value_data.value,
                        sort_order=spec_value_data.sort_order
                    )
                    db.add(spec_value)
                    db.flush()  # 取得規格值的 ID
                    spec_value_map[spec_group_data.sort_order][spec_value_data.value] = spec_value.id
            
            # 建立新的變體
            for variant_data in variants_data:
                # 查找第一層規格值ID
                spec_value_1_id = spec_value_map[1].get(variant_data.spec_value_1)
                if not spec_value_1_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"變體的第一層規格值 '{variant_data.spec_value_1}' 不在規格組中"
                    )
                
                # 查找第二層規格值ID（如果存在）
                spec_value_2_id = None
                if variant_data.spec_value_2:
                    if 2 not in spec_value_map:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="變體包含第二層規格值，但商品只有一個規格組"
                        )
                    spec_value_2_id = spec_value_map[2].get(variant_data.spec_value_2)
                    if not spec_value_2_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"變體的第二層規格值 '{variant_data.spec_value_2}' 不在規格組中"
                        )
                
                # 使用儲存的規格組ID
                spec_group_1_id = spec_group_map.get(1)
                spec_group_2_id = spec_group_map.get(2)
                
                variant = ProductVariant(
                    product_id=product.id,
                    spec_group_1_id=spec_group_1_id,
                    spec_value_1_id=spec_value_1_id,
                    spec_group_2_id=spec_group_2_id,
                    spec_value_2_id=spec_value_2_id,
                    price=variant_data.price,
                    stock=variant_data.stock
                )
                db.add(variant)
        
        # 重新計算商品 stock（變體庫存總和）
        db.flush()  # 確保所有變更都寫入資料庫
        db.refresh(product)  # 重新載入商品及其關聯
        
        if product.variants:
            product.stock = sum(variant.stock for variant in product.variants)
        else:
            logger.warning(f"商品 ID {product.id} 沒有變體，無法自動計算 stock")
        
        db.commit()
        db.refresh(product)
        
        logger.info(f"更新商品成功：{product.name}")
        
        return get_product_by_id(db, product_id, include_inactive=True)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新商品時發生錯誤：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新商品失敗：{str(e)}"
        )


def delete_product(db: Session, product_id: int) -> dict:
    """刪除商品（完全刪除）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    # 記錄商品名稱以便日誌
    product_name = product.name
    
    # 刪除商品（由於 cascade='all, delete-orphan'，相關的 images、spec_groups、variants 會自動刪除）
    db.delete(product)
    db.commit()
    
    logger.info(f"刪除商品成功：{product_name}")
    
    return {"message": "商品已刪除"}
