from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app import Base

class Carousel(Base):
    """輪播圖"""
    __tablename__ = 'carousels'
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False, index=True)
    title = Column(String(100), nullable=True)  # 標題（選填）
    image_url = Column(String(255), nullable=False)  # 圖片路徑
    link_url = Column(String(255), nullable=True)  # 點擊後跳轉的連結（選填）
    display_order = Column(Integer, default=0)  # 顯示順序
    is_active = Column(Boolean, default=True)  # 是否啟用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Carousel {self.title or self.id}>'


class StoreInfo(Base):
    """商店資訊設定"""
    __tablename__ = 'store_info'
    __table_args__ = (
        UniqueConstraint('store_id', name='uq_store_info_per_store'),
    )
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False, index=True)
    store_name = Column(String(100), nullable=False)  # 商店名稱
    store_description = Column(Text, nullable=True)  # 商店描述
    contact_email = Column(String(100), nullable=True)  # 聯絡信箱
    contact_phone = Column(String(20), nullable=True)  # 聯絡電話
    address = Column(String(255), nullable=True)  # 地址
    business_hours = Column(String(200), nullable=True)  # 營業時間
    logo_url = Column(String(255), nullable=True)  # Logo 路徑
    favicon_url = Column(String(255), nullable=True)  # Favicon 路徑
    
    # 社群媒體連結（選填）
    facebook_url = Column(String(255), nullable=True)
    instagram_url = Column(String(255), nullable=True)
    line_url = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<StoreInfo {self.store_name}>'
