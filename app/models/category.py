from sqlalchemy import Column, Integer, String, Boolean, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app import Base

# Base 類別用於模型定義 (提供 ORM 功能：將 Python 類別映射到資料庫表格) Base = declarative_base()
class Category(Base):
    __tablename__ = 'categories'
    __table_args__ = (
        # sort_order 唯一性約束（改為結合 store_id，同一商店內 sort_order 唯一）
        UniqueConstraint('store_id', 'sort_order', name='uq_store_category_sort_order'),
        # 名稱在同一店家中不能重複
        UniqueConstraint('store_id', 'name', name='uq_store_category_name'),
    )
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, nullable=True)  # 排序：非必填，購物網站顯示分類時依照排序由小到大排序，值不能重複
    is_active = Column(Boolean, default=True)  # 是否生效：true的時候才會顯示在購物網站，false不顯示
    
    # 關聯設定：一對多
    products = relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'
