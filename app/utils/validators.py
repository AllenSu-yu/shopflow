from pydantic import BaseModel, Field, validator, EmailStr, root_validator
from typing import Optional, List
from datetime import datetime


# ==================== Auth Validators ====================

class CustomerRegister(BaseModel):
    """客戶註冊"""
    email: EmailStr = Field(..., description="電子郵件")
    password: str = Field(..., min_length=6, max_length=50, description="密碼")
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, max_length=255, description="地址")
    
    @validator('email', 'name', 'phone', 'address', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


class CustomerLogin(BaseModel):
    """客戶登入"""
    email: EmailStr = Field(..., description="電子郵件")
    password: str = Field(..., min_length=6, max_length=50, description="密碼")


class AdminLogin(BaseModel):
    """管理員登入"""
    username: str = Field(..., min_length=1, max_length=50, description="使用者名稱")
    password: str = Field(..., min_length=6, max_length=50, description="密碼")
    
    @validator('username', pre=True)
    def strip_username(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip()
        return v


# ==================== Product Validators ====================

class ProductImageCreate(BaseModel):
    """商品圖片建立"""
    image_url: str = Field(..., description="圖片路徑")
    is_primary: bool = Field(False, description="是否為主圖")
    display_order: int = Field(0, description="顯示順序")


class ProductSpecValueCreate(BaseModel):
    """規格值建立（例如：S、M、L、XL、黑色、白色）"""
    value: str = Field(..., min_length=1, max_length=100, description="規格值")
    sort_order: int = Field(0, description="顯示順序")
    
    @validator('value', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip()
        return v


class ProductSpecGroupCreate(BaseModel):
    """規格組建立（例如：尺寸、顏色）
    每個商品可以有1-2個規格組，sort_order 用於區分第一層（1）和第二層（2）
    第一層最多5個選項，第二層最多5個選項
    """
    name: str = Field(..., min_length=1, max_length=50, description="規格組名稱（如：尺寸、顏色）")
    sort_order: int = Field(..., ge=1, le=2, description="排序：1 表示第一層規格，2 表示第二層規格")
    values: List[ProductSpecValueCreate] = Field(..., min_items=1, max_items=5, description="規格值列表（至少1個，最多5個）")
    
    @validator('name', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @validator('values')
    def validate_values_count(cls, v, values):
        """驗證規格值數量"""
        if not v or len(v) == 0:
            raise ValueError("規格組必須至少有一個規格值")
        if len(v) > 5:
            raise ValueError("每個規格組最多只能有5個選項")
        return v


class ProductVariantCreate(BaseModel):
    """商品變體建立（規格組合的價格和庫存）
    支援兩種模式：
    1. 單層規格：只有 spec_value_1，spec_value_2 為 None
    2. 兩層規格：有 spec_value_1 和 spec_value_2
    """
    spec_value_1: str = Field(..., description="第一層規格值（必填）")
    spec_value_2: Optional[str] = Field(None, description="第二層規格值（可選，NULL 表示只有一層規格）")
    price: float = Field(..., gt=0, description="該組合的價格")
    stock: int = Field(..., ge=0, description="該組合的庫存")
    
    @validator('spec_value_1', 'spec_value_2', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


class ProductCreate(BaseModel):
    """商品建立
    支援兩種規格模式：
    1. 單層規格：只有一個規格組（sort_order=1），variants 中 spec_value_2 為 None
    2. 兩層規格：有兩個規格組（sort_order=1 和 sort_order=2），variants 中 spec_value_2 不為 None
    
    限制：
    - 第一層規格最多5個選項
    - 第二層規格最多5個選項
    - 總共最多25種組合（5x5=25）
    
    注意：價格由 variants 中的每個變體決定，商品本身沒有價格
    """
    name: str = Field(..., min_length=1, max_length=100, description="商品名稱")
    description: Optional[str] = Field(None, description="商品描述")
    category_id: int = Field(..., gt=0, description="分類ID")
    is_active: bool = Field(True, description="是否啟用")
    images: Optional[List[ProductImageCreate]] = Field([], description="商品圖片列表")
    spec_groups: List[ProductSpecGroupCreate] = Field(..., min_items=1, max_items=2, description="規格組列表（必填，1-2個）")
    variants: List[ProductVariantCreate] = Field(..., min_items=1, max_items=25, description="商品變體列表（必填，至少1個，最多25個）")
    
    @validator('name', 'description', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v
    
    @validator('spec_groups')
    def validate_spec_groups(cls, v):
        """驗證規格組"""
        if not v or len(v) == 0:
            raise ValueError("商品必須至少有一個規格組")
        if len(v) > 2:
            raise ValueError("商品規格組數量不能超過2個")
        
        # 檢查 sort_order 是否唯一且符合要求
        sort_orders = [group.sort_order for group in v]
        if len(sort_orders) != len(set(sort_orders)):
            raise ValueError("規格組的 sort_order 不能重複")
        
        if len(v) == 2:
            if 1 not in sort_orders or 2 not in sort_orders:
                raise ValueError("兩個規格組時，sort_order 必須為 1 和 2")
        else:
            if sort_orders[0] != 1:
                raise ValueError("單個規格組時，sort_order 必須為 1")
        
        # 檢查每個規格組的選項數量限制
        for group in v:
            if group.sort_order == 1:
                if len(group.values) > 5:
                    raise ValueError("第一層規格最多只能有5個選項")
            elif group.sort_order == 2:
                if len(group.values) > 5:
                    raise ValueError("第二層規格最多只能有5個選項")
        
        return v
    
    @validator('variants')
    def validate_variants(cls, v, values):
        """驗證變體與規格組的一致性"""
        if not v or len(v) == 0:
            raise ValueError("商品必須至少有一個變體")
        
        # 檢查變體總數限制
        if len(v) > 25:
            raise ValueError("商品變體總數不能超過25個（第一層最多5個選項 × 第二層最多5個選項）")
        
        # 檢查變體中的規格值是否都在規格組中
        spec_groups = values.get('spec_groups', [])
        if not spec_groups:
            return v
        
        # 建立規格值映射
        spec_values_map = {}
        for group in spec_groups:
            spec_values_map[group.sort_order] = {val.value for val in group.values}
        
        # 檢查組合數量是否超過限制
        if len(spec_groups) == 2:
            # 兩層規格：最多 5x5 = 25 種組合
            group1_values_count = len(spec_values_map.get(1, set()))
            group2_values_count = len(spec_values_map.get(2, set()))
            max_combinations = group1_values_count * group2_values_count
            if len(v) > max_combinations:
                raise ValueError(f"變體數量不能超過規格組合的最大數量：{max_combinations}（第一層{group1_values_count}個選項 × 第二層{group2_values_count}個選項）")
        else:
            # 單層規格：最多 5 個變體
            group1_values_count = len(spec_values_map.get(1, set()))
            if len(v) > group1_values_count:
                raise ValueError(f"變體數量不能超過第一層規格的選項數量：{group1_values_count}")
        
        for variant in v:
            # 檢查第一層規格值
            if variant.spec_value_1 not in spec_values_map.get(1, set()):
                raise ValueError(f"變體的第一層規格值 '{variant.spec_value_1}' 不在規格組中")
            
            # 如果有第二層規格值，檢查是否在第二層規格組中
            if variant.spec_value_2:
                if len(spec_groups) < 2:
                    raise ValueError("變體包含第二層規格值，但商品只有一個規格組")
                if variant.spec_value_2 not in spec_values_map.get(2, set()):
                    raise ValueError(f"變體的第二層規格值 '{variant.spec_value_2}' 不在規格組中")
            else:
                # 如果沒有第二層規格值，但商品有兩個規格組，這也是允許的（單層規格模式）
                pass
        
        return v


class ProductUpdate(BaseModel):
    """商品更新（stock 由變體庫存總和自動計算，不可直接更新）
    注意：價格由 variants 決定，商品本身沒有價格欄位
    
    支援更新：
    - 基本資訊（name, description, category_id, is_active）
    - 規格組和變體（spec_groups, variants）- 可選，如果提供則會完全替換現有的規格組和變體
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="商品名稱")
    description: Optional[str] = Field(None, description="商品描述")
    category_id: Optional[int] = Field(None, gt=0, description="分類ID")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    spec_groups: Optional[List[ProductSpecGroupCreate]] = Field(None, description="規格組列表（可選，如果提供則會替換現有的規格組）")
    variants: Optional[List[ProductVariantCreate]] = Field(None, description="商品變體列表（可選，如果提供則會替換現有的變體）")
    # 注意：stock 欄位已移除，因為商品 stock 由變體庫存總和自動計算
    
    @validator('name', 'description', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v
    
    @validator('spec_groups')
    def validate_spec_groups_update(cls, v):
        """驗證規格組（更新時）"""
        if v is None:
            return v
        
        if len(v) == 0:
            raise ValueError("規格組不能為空，如果不需要規格組請不要提供此欄位")
        if len(v) > 2:
            raise ValueError("商品規格組數量不能超過2個")
        
        # 檢查 sort_order 是否唯一且符合要求
        sort_orders = [group.sort_order for group in v]
        if len(sort_orders) != len(set(sort_orders)):
            raise ValueError("規格組的 sort_order 不能重複")
        
        if len(v) == 2:
            if 1 not in sort_orders or 2 not in sort_orders:
                raise ValueError("兩個規格組時，sort_order 必須為 1 和 2")
        else:
            if sort_orders[0] != 1:
                raise ValueError("單個規格組時，sort_order 必須為 1")
        
        # 檢查每個規格組的選項數量限制
        for group in v:
            if group.sort_order == 1:
                if len(group.values) > 5:
                    raise ValueError("第一層規格最多只能有5個選項")
            elif group.sort_order == 2:
                if len(group.values) > 5:
                    raise ValueError("第二層規格最多只能有5個選項")
        
        return v
    
    @validator('variants')
    def validate_variants_update(cls, v):
        """驗證變體（更新時）- 基本驗證"""
        if v is None:
            return v
        
        if len(v) == 0:
            raise ValueError("變體不能為空，如果不需要變體請不要提供此欄位")
        
        # 檢查變體總數限制
        if len(v) > 25:
            raise ValueError("商品變體總數不能超過25個（第一層最多5個選項 × 第二層最多5個選項）")
        
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_spec_groups_and_variants_consistency(cls, values):
        """驗證規格組和變體的一致性（更新時）"""
        spec_groups = values.get('spec_groups')
        variants = values.get('variants')
        
        # 如果提供了 spec_groups 或 variants，必須同時提供兩者
        if (spec_groups is not None) != (variants is not None):
            raise ValueError("更新商品時，spec_groups 和 variants 必須同時提供或同時不提供")
        
        # 如果兩者都提供了，檢查一致性
        if spec_groups is not None and variants is not None:
            # 建立規格值映射
            spec_values_map = {}
            for group in spec_groups:
                spec_values_map[group.sort_order] = {val.value for val in group.values}
            
            # 檢查組合數量是否超過限制
            if len(spec_groups) == 2:
                group1_values_count = len(spec_values_map.get(1, set()))
                group2_values_count = len(spec_values_map.get(2, set()))
                max_combinations = group1_values_count * group2_values_count
                if len(variants) > max_combinations:
                    raise ValueError(f"變體數量不能超過規格組合的最大數量：{max_combinations}（第一層{group1_values_count}個選項 × 第二層{group2_values_count}個選項）")
            else:
                group1_values_count = len(spec_values_map.get(1, set()))
                if len(variants) > group1_values_count:
                    raise ValueError(f"變體數量不能超過第一層規格的選項數量：{group1_values_count}")
            
            # 檢查變體中的規格值是否都在規格組中
            for variant in variants:
                if variant.spec_value_1 not in spec_values_map.get(1, set()):
                    raise ValueError(f"變體的第一層規格值 '{variant.spec_value_1}' 不在規格組中")
                
                if variant.spec_value_2:
                    if len(spec_groups) < 2:
                        raise ValueError("變體包含第二層規格值，但商品只有一個規格組")
                    if variant.spec_value_2 not in spec_values_map.get(2, set()):
                        raise ValueError(f"變體的第二層規格值 '{variant.spec_value_2}' 不在規格組中")
        
        return values


# ==================== Order Validators ====================

class OrderItemCreate(BaseModel):
    """訂單項目建立"""
    product_id: int = Field(..., gt=0, description="商品ID")
    quantity: int = Field(..., gt=0, description="數量")
    spec_info: Optional[str] = Field(None, max_length=200, description="規格資訊")


class OrderCreate(BaseModel):
    """訂單建立（items 會從購物車自動取得）"""
    recipient_name: str = Field(..., min_length=1, max_length=50, description="收件人姓名")
    recipient_phone: str = Field(..., min_length=1, max_length=20, description="收件人電話")
    recipient_address: str = Field(..., min_length=1, max_length=255, description="收件地址")
    payment_method: Optional[str] = Field(None, max_length=50, description="付款方式")
    shipping_method: Optional[str] = Field(None, max_length=50, description="物流方式")
    
    @validator('recipient_name', 'recipient_phone', 'recipient_address', 'payment_method', 'shipping_method', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


class OrderUpdate(BaseModel):
    """訂單更新（後台使用）"""
    status: Optional[str] = Field(None, description="訂單狀態")
    payment_status: Optional[str] = Field(None, description="付款狀態")
    tracking_number: Optional[str] = Field(None, max_length=100, description="物流追蹤號碼")
    shipping_method: Optional[str] = Field(None, max_length=50, description="物流方式")
    
    @validator('tracking_number', 'shipping_method', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


# ==================== Cart Validators ====================

class CartItemCreate(BaseModel):
    """購物車項目建立"""
    product_id: int = Field(..., gt=0, description="商品ID")
    quantity: int = Field(..., gt=0, description="數量")
    spec_info: Optional[str] = Field(None, max_length=200, description="規格資訊")


class CartItemBatchCreate(BaseModel):
    """購物車批次加入"""
    items: List[CartItemCreate] = Field(..., min_items=1, max_items=50, description="購物車項目列表（每項含 product_id, quantity, spec_info）")


class CartItemUpdate(BaseModel):
    """購物車項目更新"""
    quantity: int = Field(..., gt=0, description="數量")


# ==================== Category Validators ====================

class CategoryCreate(BaseModel):
    """分類建立"""
    name: str = Field(..., min_length=1, max_length=50, description="分類名稱")
    sort_order: Optional[int] = Field(None, description="排序：非必填，購物網站顯示分類時依照排序由小到大排序")
    is_active: Optional[bool] = Field(True, description="是否生效：true的時候才會顯示在購物網站，false不顯示")
    
    @validator('name', pre=True)
    def strip_name(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip()
        return v


class CategoryUpdate(BaseModel):
    """分類更新"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="分類名稱")
    sort_order: Optional[int] = Field(None, description="排序：非必填，購物網站顯示分類時依照排序由小到大排序")
    is_active: Optional[bool] = Field(None, description="是否生效：true的時候才會顯示在購物網站，false不顯示")
    
    @validator('name', pre=True)
    def strip_name(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


# ==================== CMS Validators ====================

class CarouselCreate(BaseModel):
    """輪播圖建立"""
    title: Optional[str] = Field(None, max_length=100, description="標題")
    image_url: str = Field(..., description="圖片路徑")
    link_url: Optional[str] = Field(None, max_length=255, description="連結網址")
    display_order: int = Field(0, description="顯示順序")
    is_active: bool = Field(True, description="是否啟用")
    
    @validator('title', 'link_url', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


class CarouselUpdate(BaseModel):
    """輪播圖更新"""
    title: Optional[str] = Field(None, max_length=100, description="標題")
    image_url: Optional[str] = Field(None, description="圖片路徑")
    link_url: Optional[str] = Field(None, max_length=255, description="連結網址")
    display_order: Optional[int] = Field(None, description="顯示順序")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    
    @validator('title', 'link_url', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v


class StoreInfoUpdate(BaseModel):
    """商店資訊更新"""
    store_name: Optional[str] = Field(None, min_length=1, max_length=100, description="商店名稱")
    store_description: Optional[str] = Field(None, description="商店描述")
    contact_email: Optional[EmailStr] = Field(None, description="聯絡信箱")
    contact_phone: Optional[str] = Field(None, max_length=20, description="聯絡電話")
    address: Optional[str] = Field(None, max_length=255, description="地址")
    business_hours: Optional[str] = Field(None, max_length=200, description="營業時間")
    logo_url: Optional[str] = Field(None, description="Logo 路徑")
    favicon_url: Optional[str] = Field(None, description="Favicon 路徑")
    facebook_url: Optional[str] = Field(None, max_length=255, description="Facebook 連結")
    instagram_url: Optional[str] = Field(None, max_length=255, description="Instagram 連結")
    line_url: Optional[str] = Field(None, max_length=255, description="LINE 連結")
    
    @validator('store_name', 'contact_phone', 'address', 'business_hours', 
               'facebook_url', 'instagram_url', 'line_url', pre=True)
    def strip_strings(cls, v):
        """自動去除前後空白"""
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v
