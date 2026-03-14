from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app import templates

router = APIRouter()

# ==================== 前台頁面路由 ====================

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """前台首頁"""
    user = None
    token = request.cookies.get("token")
    if token:
        try:
            # 這裡可以從 cookie 或 session 獲取用戶資訊
            pass
        except:
            pass
    return templates.TemplateResponse("customer/index.html", {"request": request, "user": user})

@router.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    """商品列表頁"""
    return templates.TemplateResponse("customer/products.html", {"request": request})

@router.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail_page(request: Request, product_id: int):
    """商品詳情頁"""
    return templates.TemplateResponse("customer/product_detail.html", {"request": request})

@router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    """購物車頁"""
    return templates.TemplateResponse("customer/cart.html", {"request": request})

@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """結帳頁"""
    return templates.TemplateResponse("customer/checkout.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登入頁"""
    return templates.TemplateResponse("customer/login.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """註冊頁"""
    return templates.TemplateResponse("customer/register.html", {"request": request})

@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """訂單列表頁"""
    return templates.TemplateResponse("customer/orders.html", {"request": request})

@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(request: Request, order_id: int):
    """訂單詳情頁"""
    return templates.TemplateResponse("customer/order_detail.html", {"request": request})

# ==================== 後台頁面路由 ====================

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """後台登入頁"""
    return templates.TemplateResponse("admin/login.html", {"request": request})

@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request):
    """後台首頁（重定向到商品管理）"""
    return RedirectResponse(url="/admin/products")

@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products_page(request: Request):
    """後台商品管理頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse("admin/products.html", {"request": request})

@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders_page(request: Request):
    """後台訂單管理頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse("admin/orders.html", {"request": request})

@router.get("/admin/orders/{order_id}", response_class=HTMLResponse)
async def admin_order_detail_page(request: Request, order_id: int):
    """後台訂單詳情頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse("admin/order_detail.html", {"request": request})

@router.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories_page(request: Request):
    """後台分類管理頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse("admin/categories.html", {"request": request})

@router.get("/admin/cms", response_class=HTMLResponse)
async def admin_cms_page(request: Request):
    """後台商店與首頁設定頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse("admin/cms.html", {"request": request})
