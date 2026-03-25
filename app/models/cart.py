from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app import Base

class Cart(Base):
    """購物車（每個跨店客戶都會有不同的購物車，因為客戶本身也是隔離的，這裡我們加上 store_id 以加速查詢與驗證）"""
    __tablename__ = 'carts'
    __table_args__ = (
        UniqueConstraint('store_id', 'customer_id', name='uq_store_cart_customer'),
    )
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯設定：一對多
    items = relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Cart for Customer {self.customer_id}>'


class CartItem(Base):
    """購物車項目"""
    __tablename__ = 'cart_items'
    
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    
    # 規格資訊（如果有）
    spec_info = Column(String(200), nullable=True)  # 規格資訊（JSON 字串或簡單字串）
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CartItem Product {self.product_id} x {self.quantity}>'
