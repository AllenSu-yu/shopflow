from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app import Base

class Store(Base):
    """商店 (租戶) 模型"""
    __tablename__ = 'stores'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False, unique=True, index=True)  # URL 網址代碼 (e.g. store-a)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    users = relationship('User', backref='store', lazy=True, cascade='all, delete-orphan')
    customers = relationship('Customer', backref='store', lazy=True, cascade='all, delete-orphan')
    categories = relationship('Category', backref='store', lazy=True, cascade='all, delete-orphan')
    products = relationship('Product', backref='store', lazy=True, cascade='all, delete-orphan')
    orders = relationship('Order', backref='store', lazy=True, cascade='all, delete-orphan')
    carousels = relationship('Carousel', backref='store', lazy=True, cascade='all, delete-orphan')
    store_info = relationship('StoreInfo', backref='store', uselist=False, lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Store {self.name} ({self.slug})>'
