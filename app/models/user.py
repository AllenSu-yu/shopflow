from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app import Base

class User(Base):
    """後台管理員用戶"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)  # 加密後的密碼
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'


class Customer(Base):
    """前台客戶"""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)  # 加密後的密碼
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯設定：一對多
    orders = relationship('Order', backref='customer', lazy=True)
    cart = relationship('Cart', backref='customer', uselist=False, lazy=True)

    def __repr__(self):
        return f'<Customer {self.name} ({self.email})>'
