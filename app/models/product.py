from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app import Base

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    stock = Column(Integer, default=0)  # 總庫存（由 variants 庫存總和自動計算）
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)  # 商品是否啟用
    
    # 外鍵：指向 categories 表
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    
    # 關聯設定：一對多
    images = relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan')
    spec_groups = relationship('ProductSpecGroup', backref='product', lazy=True, cascade='all, delete-orphan', order_by='ProductSpecGroup.sort_order')
    variants = relationship('ProductVariant', backref='product', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.name}>'


class ProductImage(Base):
    __tablename__ = 'product_images'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    image_url = Column(String(255), nullable=False)  # 圖片路徑
    is_primary = Column(Boolean, default=False)  # 是否為主圖
    display_order = Column(Integer, default=0)  # 顯示順序

    def __repr__(self):
        return f'<ProductImage {self.id} for Product {self.product_id}>'


class ProductSpecGroup(Base):
    """規格組表（例如：尺寸、顏色）
    每個商品可以有1-2個規格組，sort_order 用於區分第一層和第二層
    第一層最多5個選項，第二層最多5個選項
    """
    __tablename__ = 'product_spec_groups'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    name = Column(String(50), nullable=False)  # 規格組名稱（如：尺寸、顏色）
    sort_order = Column(Integer, nullable=False)  # 排序：1 表示第一層規格，2 表示第二層規格
    
    # 關聯設定：一對多
    spec_values = relationship('ProductSpecValue', backref='spec_group', lazy=True, cascade='all, delete-orphan', order_by='ProductSpecValue.sort_order')
    
    # 唯一性約束：同一商品不能有重複的 sort_order
    __table_args__ = (
        UniqueConstraint('product_id', 'sort_order', name='uq_product_spec_group_sort_order'),
    )

    def __repr__(self):
        return f'<ProductSpecGroup {self.name} (sort_order={self.sort_order}) for Product {self.product_id}>'


class ProductSpecValue(Base):
    """規格值表（例如：S、M、L、XL、黑色、白色）
    屬於某個規格組
    """
    __tablename__ = 'product_spec_values'
    
    id = Column(Integer, primary_key=True)
    spec_group_id = Column(Integer, ForeignKey('product_spec_groups.id'), nullable=False)
    value = Column(String(100), nullable=False)  # 規格值（如：S、M、L、XL、黑色、白色）
    sort_order = Column(Integer, default=0)  # 顯示順序
    
    # 唯一性約束：同一規格組內不能有重複的值
    __table_args__ = (
        UniqueConstraint('spec_group_id', 'value', name='uq_spec_group_value'),
    )

    def __repr__(self):
        return f'<ProductSpecValue {self.value} for SpecGroup {self.spec_group_id}>'


class ProductVariant(Base):
    """商品變體表（規格組合）
    存儲每個規格組合的價格和庫存
    
    支援兩種模式：
    1. 單層規格：只有 spec_group_1_id 和 spec_value_1_id，spec_group_2_id 和 spec_value_2_id 為 NULL
    2. 兩層規格：有 spec_group_1_id、spec_value_1_id、spec_group_2_id、spec_value_2_id
    
    限制：
    - 第一層最多5個選項，第二層最多5個選項
    - 總共最多25種組合（5x5=25）
    """
    __tablename__ = 'product_variants'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    
    # 第一層規格（必填）
    spec_group_1_id = Column(Integer, ForeignKey('product_spec_groups.id'), nullable=False)
    spec_value_1_id = Column(Integer, ForeignKey('product_spec_values.id'), nullable=False)
    
    # 第二層規格（可選，NULL 表示只有一層規格）
    spec_group_2_id = Column(Integer, ForeignKey('product_spec_groups.id'), nullable=True)
    spec_value_2_id = Column(Integer, ForeignKey('product_spec_values.id'), nullable=True)
    
    price = Column(Float, nullable=False, default=0.0)  # 該組合的價格
    stock = Column(Integer, default=0)  # 該組合的庫存
    
    # 關聯設定
    spec_group_1 = relationship('ProductSpecGroup', foreign_keys=[spec_group_1_id])
    spec_value_1 = relationship('ProductSpecValue', foreign_keys=[spec_value_1_id])
    spec_group_2 = relationship('ProductSpecGroup', foreign_keys=[spec_group_2_id])
    spec_value_2 = relationship('ProductSpecValue', foreign_keys=[spec_value_2_id])
    
    # 唯一性約束：同一商品不能有重複的規格組合
    __table_args__ = (
        UniqueConstraint('product_id', 'spec_value_1_id', 'spec_value_2_id', name='uq_product_variant_combination'),
    )

    def __repr__(self):
        if self.spec_value_2_id:
            return f'<ProductVariant {self.product_id}: {self.spec_value_1_id}+{self.spec_value_2_id}>'
        else:
            return f'<ProductVariant {self.product_id}: {self.spec_value_1_id}>'
