from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app import Base

class OrderStatus(enum.Enum):
    """訂單狀態枚舉"""
    PENDING = "pending"  # 待處理
    PAID = "paid"  # 已付款
    SHIPPED = "shipped"  # 已出貨
    CANCELLED = "cancelled"  # 已取消

class Order(Base):
    __tablename__ = 'orders'
    __table_args__ = (
        UniqueConstraint('store_id', 'order_number', name='uq_store_order_number'),
    )
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False, index=True)
    order_number = Column(String(50), nullable=False)  # 訂單編號
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    
    # 訂單狀態
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    # 支付紀錄 ID (用於 TapPay 退款)
    payment_rec_id = Column(String(100), nullable=True)
    
    # 金額資訊
    subtotal = Column(Float, nullable=False, default=0.0)  # 小計
    shipping_fee = Column(Float, nullable=False, default=0.0)  # 運費
    total = Column(Float, nullable=False, default=0.0)  # 總金額
    
    # 收件資訊
    recipient_name = Column(String(50), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    recipient_address = Column(String(255), nullable=False)
    
    # 付款資訊
    payment_method = Column(String(50), nullable=True)  # 付款方式（如：信用卡、貨到付款）
    payment_status = Column(String(20), default='unpaid')  # 付款狀態（unpaid, paid, refunded）
    
    # 出貨資訊
    shipping_method = Column(String(50), nullable=True)  # 物流方式
    tracking_number = Column(String(100), nullable=True)  # 物流追蹤號碼
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shipped_at = Column(DateTime, nullable=True)  # 出貨時間
    delivered_at = Column(DateTime, nullable=True)  # 送達時間
    
    # 關聯設定：一對多
    items = relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.order_number}>'


class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    
    # 商品資訊快照（避免商品資訊變更影響歷史訂單）
    product_name = Column(String(100), nullable=False)
    product_price = Column(Float, nullable=False)  # 下單時的價格
    quantity = Column(Integer, nullable=False, default=1)
    
    # 規格資訊（如果有）
    spec_info = Column(String(200), nullable=True)  # 規格資訊（JSON 字串或簡單字串）
    
    # 小計
    subtotal = Column(Float, nullable=False)  # quantity * product_price

    def __repr__(self):
        return f'<OrderItem {self.product_name} x {self.quantity}>'
