from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from datetime import datetime
from typing import Optional
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductVariant
from app.models.cart import Cart, CartItem
from app.models.user import Customer
from app.utils.validators import OrderCreate, OrderUpdate
import logging
import json

logger = logging.getLogger(__name__)


def generate_order_number() -> str:
    """生成訂單編號（格式：ORD + 時間戳 + 隨機數）"""
    import random
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_num = random.randint(1000, 9999)
    return f"ORD{timestamp}{random_num}"


def create_order(db: Session, customer_id: int, order_data: OrderCreate) -> dict:
    """建立訂單（items 從購物車取得）"""
    # 檢查客戶是否存在
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="客戶不存在"
        )
    
    # 取得購物車
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="購物車為空，無法建立訂單"
        )
    
    # 取得購物車項目
    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="購物車為空，無法建立訂單"
        )
    
    # 計算訂單金額
    subtotal = 0.0
    order_items_data = []
    
    for cart_item in cart_items:
        # 檢查商品是否存在且啟用
        product = db.query(Product).options(
            joinedload(Product.variants)
        ).filter(
            Product.id == cart_item.product_id,
            Product.is_active  # Boolean 欄位直接使用即可
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"商品 ID {cart_item.product_id} 不存在或已下架，請先從購物車移除"
            )
        
        # 必須有規格資訊才能確定價格和庫存
        if not cart_item.spec_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"商品「{product.name}」必須選擇規格才能下單，請先從購物車移除後重新加入"
            )
        
        variant = None
        item_price = 0.0
        
        try:
            spec_data = json.loads(cart_item.spec_info) if isinstance(cart_item.spec_info, str) else cart_item.spec_info
            variant_id = spec_data.get('variant_id')
            if not variant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"商品「{product.name}」的規格資訊中缺少 variant_id"
                )
            
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == variant_id,
                ProductVariant.product_id == product.id
            ).first()
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"商品「{product.name}」的規格組合不存在，請先從購物車移除"
                )
            if variant.stock < cart_item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"商品「{product.name}」的該規格組合庫存不足，目前庫存：{variant.stock}，購物車數量：{cart_item.quantity}"
                )
            item_price = variant.price
        except (json.JSONDecodeError, KeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"商品「{product.name}」的規格資訊格式錯誤：{str(e)}"
            )
        
        # 計算小計
        item_subtotal = item_price * cart_item.quantity
        subtotal += item_subtotal
        
        # 儲存訂單項目資料
        order_items_data.append({
            "product": product,
            "variant": variant,
            "product_name": product.name,
            "product_price": item_price,
            "quantity": cart_item.quantity,
            "spec_info": cart_item.spec_info,
            "subtotal": item_subtotal
        })
    
    # 計算運費（簡化版本，可以根據實際需求調整）
    shipping_fee = 100.0  # 預設運費
    total = subtotal + shipping_fee
    
    # 生成訂單編號
    order_number = generate_order_number()
    
    # 建立訂單
    new_order = Order(
        order_number=order_number,
        customer_id=customer_id,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=total,
        recipient_name=order_data.recipient_name,
        recipient_phone=order_data.recipient_phone,
        recipient_address=order_data.recipient_address,
        payment_method=order_data.payment_method,
        shipping_method=order_data.shipping_method,
        payment_status="unpaid"
    )
    
    db.add(new_order)
    db.flush()  # 取得訂單 ID
    
    # 建立訂單項目並更新商品庫存
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item_data["product"].id,
            product_name=item_data["product_name"],
            product_price=item_data["product_price"],
            quantity=item_data["quantity"],
            spec_info=item_data["spec_info"],
            subtotal=item_data["subtotal"]
        )
        db.add(order_item)
        
        # 更新庫存
        if item_data["variant"]:
            # 更新變體庫存
            item_data["variant"].stock -= item_data["quantity"]
            # 重新計算商品總庫存
            product = item_data["product"]
            product.stock = sum(v.stock for v in product.variants)
        else:
            # 更新商品總庫存
            item_data["product"].stock -= item_data["quantity"]
    
    # 清空購物車
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    
    db.commit()
    db.refresh(new_order)
    
    logger.info(f"建立訂單成功：{order_number}")
    
    return get_order_by_id(db, new_order.id)


def get_orders_by_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 20) -> dict:
    """取得客戶的訂單列表"""
    query = db.query(Order).filter(Order.customer_id == customer_id)
    
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    orders_list = []
    for order in orders:
        orders_list.append({
            "id": order.id,
            "order_number": order.order_number,
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


def get_order_by_id(db: Session, order_id: int, customer_id: Optional[int] = None) -> dict:
    """取得訂單詳情"""
    query = db.query(Order).filter(Order.id == order_id)
    
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    
    order = query.first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="訂單不存在"
        )
    
    items_list = []
    for item in order.items:
        items_list.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "product_price": item.product_price,
            "quantity": item.quantity,
            "spec_info": item.spec_info,
            "subtotal": item.subtotal
        })
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id,
        "status": order.status.value,
        "subtotal": order.subtotal,
        "shipping_fee": order.shipping_fee,
        "total": order.total,
        "recipient_name": order.recipient_name,
        "recipient_phone": order.recipient_phone,
        "recipient_address": order.recipient_address,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "shipping_method": order.shipping_method,
        "tracking_number": order.tracking_number,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "items": items_list
    }


def update_order_status(
    db: Session,
    order_id: int,
    order_data: OrderUpdate
) -> dict:
    """更新訂單狀態（後台使用）"""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="訂單不存在"
        )
    
    # 更新狀態
    if order_data.status:
        try:
            new_status = OrderStatus(order_data.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的訂單狀態：{order_data.status}"
            )
        
        # 狀態轉換檢核
        current_status = order.status
        
        # 檢核：已取消或已退款的訂單不應更新狀態
        if current_status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"訂單狀態為「{current_status.value}」，無法更新狀態"
            )
        
        # 檢核：更新為「已送達」時，必須先出貨
        if new_status == OrderStatus.DELIVERED:
            if current_status != OrderStatus.SHIPPED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"訂單必須先出貨（目前狀態：{current_status.value}）才能標記為已送達"
                )
        
        # 檢核：更新為「已出貨」時，訂單必須已確認或處理中
        if new_status == OrderStatus.SHIPPED:
            if current_status not in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"訂單必須先確認或處理中（目前狀態：{current_status.value}）才能出貨"
                )
        
        # 更新狀態
        order.status = new_status
        
        # 如果狀態變更為已出貨，記錄出貨時間
        if order.status == OrderStatus.SHIPPED and not order.shipped_at:
            order.shipped_at = datetime.utcnow()
        
        # 如果狀態變更為已送達，記錄送達時間
        if order.status == OrderStatus.DELIVERED and not order.delivered_at:
            order.delivered_at = datetime.utcnow()
    
    # 更新其他欄位
    if order_data.payment_status:
        order.payment_status = order_data.payment_status
    
    if order_data.tracking_number:
        order.tracking_number = order_data.tracking_number
    
    if order_data.shipping_method:
        order.shipping_method = order_data.shipping_method
    
    db.commit()
    db.refresh(order)
    
    logger.info(f"更新訂單狀態：{order.order_number} -> {order.status.value}")
    
    return get_order_by_id(db, order_id)
