from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import Customer
from app.utils.validators import CartItemCreate, CartItemUpdate, CartItemBatchCreate
import logging
import json

logger = logging.getLogger(__name__)


def get_or_create_cart(db: Session, customer_id: int) -> Cart:
    """取得或建立購物車"""
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    
    if not cart:
        cart = Cart(customer_id=customer_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        logger.info(f"為客戶 {customer_id} 建立新購物車")
    
    return cart


def add_to_cart(db: Session, customer_id: int, item_data: CartItemCreate) -> dict:
    """添加商品到購物車"""
    # 取得或建立購物車
    cart = get_or_create_cart(db, customer_id)
    
    # 檢查商品是否存在且啟用
    product = db.query(Product).options(
        joinedload(Product.variants)
    ).filter(
        Product.id == item_data.product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在或已下架"
        )
    
    # 必須有規格資訊才能確定價格和庫存
    if not item_data.spec_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"商品「{product.name}」必須選擇規格才能加入購物車"
        )
    
    # 檢查變體庫存
    variant = None
    try:
        spec_data = json.loads(item_data.spec_info) if isinstance(item_data.spec_info, str) else item_data.spec_info
        variant_id = spec_data.get('variant_id')
        if not variant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="規格資訊中缺少 variant_id"
            )
        
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product.id
        ).first()
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="規格組合不存在"
            )
        if variant.stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"該規格組合庫存不足，目前庫存：{variant.stock}"
            )
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="規格資訊格式錯誤"
        )
    
    # 檢查購物車中是否已有相同商品和規格
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item_data.product_id,
        CartItem.spec_info == item_data.spec_info
    ).first()
    
    if existing_item:
        # 更新數量
        new_quantity = existing_item.quantity + item_data.quantity
        if variant.stock < new_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"該規格組合庫存不足，目前庫存：{variant.stock}"
            )
        existing_item.quantity = new_quantity
        db.commit()
        db.refresh(existing_item)
        logger.info(f"更新購物車項目數量：{existing_item.id}")
    else:
        # 建立新項目
        new_item = CartItem(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            spec_info=item_data.spec_info
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        logger.info(f"添加商品到購物車：{item_data.product_id}")
    
    return get_cart_details(db, cart.id)


def add_to_cart_batch(db: Session, customer_id: int, batch_data: CartItemBatchCreate) -> dict:
    """批次添加商品到購物車，一次請求可加入多個商品／多個規格與數量"""
    result = None
    for item in batch_data.items:
        result = add_to_cart(db, customer_id, item)
    return result


def update_cart_item(db: Session, customer_id: int, item_id: int, item_data: CartItemUpdate) -> dict:
    """更新購物車項目數量"""
    cart = get_or_create_cart(db, customer_id)
    
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="購物車項目不存在"
        )
    
    # 檢查庫存
    product = db.query(Product).options(
        joinedload(Product.variants)
    ).filter(Product.id == cart_item.product_id).first()
    
    # 必須有規格資訊才能確定庫存
    if not cart_item.spec_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"購物車項目「{product.name}」缺少規格資訊，請重新加入購物車"
        )
    
    try:
        spec_data = json.loads(cart_item.spec_info) if isinstance(cart_item.spec_info, str) else cart_item.spec_info
        variant_id = spec_data.get('variant_id')
        if not variant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"購物車項目「{product.name}」的規格資訊中缺少 variant_id"
            )
        
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product.id
        ).first()
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"購物車項目「{product.name}」的規格組合不存在"
            )
        if variant.stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"該規格組合庫存不足，目前庫存：{variant.stock}"
            )
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"購物車項目「{product.name}」的規格資訊格式錯誤：{str(e)}"
        )
    
    cart_item.quantity = item_data.quantity
    db.commit()
    db.refresh(cart_item)
    
    logger.info(f"更新購物車項目：{item_id}")
    
    return get_cart_details(db, cart.id)


def remove_from_cart(db: Session, customer_id: int, item_id: int) -> dict:
    """從購物車移除項目"""
    cart = get_or_create_cart(db, customer_id)
    
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="購物車項目不存在"
        )
    
    db.delete(cart_item)
    db.commit()
    
    logger.info(f"移除購物車項目：{item_id}")
    
    return get_cart_details(db, cart.id)


def clear_cart(db: Session, customer_id: int) -> dict:
    """清空購物車"""
    cart = get_or_create_cart(db, customer_id)
    
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    
    logger.info(f"清空購物車：{cart.id}")
    
    return {"message": "購物車已清空", "cart": {"id": cart.id, "items": []}}


def get_cart_total(db: Session, cart_id: int) -> float:
    """計算購物車總金額"""
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart_id).all()
    
    total = 0.0
    for item in cart_items:
        product = db.query(Product).options(
            joinedload(Product.variants)
        ).filter(Product.id == item.product_id).first()
        if product:
            # 必須有規格資訊才能確定價格
            if not item.spec_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"商品「{product.name}」必須選擇規格才能加入購物車"
                )
            
            try:
                spec_data = json.loads(item.spec_info) if isinstance(item.spec_info, str) else item.spec_info
                variant_id = spec_data.get('variant_id')
                if not variant_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="規格資訊中缺少 variant_id"
                    )
                
                variant = db.query(ProductVariant).filter(
                    ProductVariant.id == variant_id,
                    ProductVariant.product_id == product.id
                ).first()
                if not variant:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="規格組合不存在"
                    )
                
                price = variant.price
            except (json.JSONDecodeError, KeyError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"規格資訊格式錯誤：{str(e)}"
                )
            
            total += price * item.quantity
    
    return total


def get_cart_details(db: Session, cart_id: int) -> dict:
    """取得購物車詳情"""
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="購物車不存在"
        )
    
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart_id).all()
    
    items_list = []
    for item in cart_items:
        product = db.query(Product).options(
            joinedload(Product.images),
            joinedload(Product.variants)
        ).filter(Product.id == item.product_id).first()
        if product:
            # 必須有規格資訊才能確定價格
            if not item.spec_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"購物車項目「{product.name}」缺少規格資訊，請重新加入購物車"
                )
            
            try:
                spec_data = json.loads(item.spec_info) if isinstance(item.spec_info, str) else item.spec_info
                variant_id = spec_data.get('variant_id')
                if not variant_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"購物車項目「{product.name}」的規格資訊中缺少 variant_id"
                    )
                
                variant = db.query(ProductVariant).options(
                    joinedload(ProductVariant.spec_value_1),
                    joinedload(ProductVariant.spec_value_2)
                ).filter(
                    ProductVariant.id == variant_id,
                    ProductVariant.product_id == product.id
                ).first()
                if not variant:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"購物車項目「{product.name}」的規格組合不存在"
                    )
                
                price = variant.price
                
                # 取得規格資訊
                variant_specs = []
                if variant.spec_value_1:
                    variant_specs.append(variant.spec_value_1.value)
                if variant.spec_value_2:
                    variant_specs.append(variant.spec_value_2.value)
                variant_spec_text = " / ".join(variant_specs) if variant_specs else None
            except (json.JSONDecodeError, KeyError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"購物車項目「{product.name}」的規格資訊格式錯誤：{str(e)}"
                )
            
            items_list.append({
                "id": item.id,
                "product_id": product.id,
                "product_name": product.name,
                "product_price": price,
                "quantity": item.quantity,
                "spec_info": item.spec_info,
                "variant_spec": variant_spec_text,
                "subtotal": price * item.quantity,
                "primary_image": next(
                    (img.image_url for img in sorted(product.images, key=lambda x: (x.display_order, x.id)) if img.is_primary),
                    product.images[0].image_url if product.images else None
                )
            })
    
    total = get_cart_total(db, cart_id)
    
    return {
        "id": cart.id,
        "customer_id": cart.customer_id,
        "items": items_list,
        "total": total,
        "item_count": len(items_list)
    }
