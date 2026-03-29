from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app import templates, get_db
from app.config import Config
from app.utils.dependencies import get_store
from sqlalchemy.orm import Session

router = APIRouter()
merchant_router = APIRouter()
admin_global_router = APIRouter()
home_router = APIRouter()

@home_router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """招商首頁"""
    return templates.TemplateResponse(request=request, name="landing.html")

@merchant_router.get("/register", response_class=HTMLResponse)
async def merchant_register_page(request: Request):
    """全球商店註冊頁面"""
    return templates.TemplateResponse(request=request, name="merchant_register.html")

@admin_global_router.get("/login", response_class=HTMLResponse)
async def unified_admin_login_page(request: Request):
    """統一後台登入入口 (URL: /shop/admin/login)"""
    return templates.TemplateResponse(request=request, name="admin/login.html")

# ==================== 前台頁面路由 ====================


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, store = Depends(get_store), db: Session = Depends(get_db)):
    """前台首頁"""
    user = None
    token = request.cookies.get("token")
    if token:
        try:
            # 這裡可以從 cookie 或 session 獲取用戶資訊
            pass
        except:
            pass
    return templates.TemplateResponse(
        request=request, 
        name="customer/index.html", 
        context={"user": user, "store": store}
    )

@router.get("/products", response_class=HTMLResponse)
async def products_page(request: Request, store = Depends(get_store), db: Session = Depends(get_db)):
    """商品列表頁"""
    return templates.TemplateResponse(request=request, name="customer/products.html", context={"store": store})

@router.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail_page(request: Request, product_id: int, store = Depends(get_store), db: Session = Depends(get_db)):
    """商品詳情頁"""
    return templates.TemplateResponse(
        request=request, 
        name="customer/product_detail.html", 
        context={"product_id": product_id, "store": store}
    )

@router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, store = Depends(get_store)):
    """購物車頁"""
    return templates.TemplateResponse(request=request, name="customer/cart.html", context={"store": store})

@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, store = Depends(get_store)):
    """結帳頁"""
    return templates.TemplateResponse(
        request=request, 
        name="customer/checkout.html", 
        context={
            "store": store,
            "tappay_app_id": Config.TAPPAY_APP_ID,
            "tappay_app_key": Config.TAPPAY_APP_KEY
        }
    )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, store = Depends(get_store)):
    """登入頁"""
    return templates.TemplateResponse(request=request, name="customer/login.html", context={"store": store})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, store = Depends(get_store)):
    """註冊頁"""
    return templates.TemplateResponse(request=request, name="customer/register.html", context={"store": store})

@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, store = Depends(get_store)):
    """訂單列表頁"""
    return templates.TemplateResponse(request=request, name="customer/orders.html", context={"store": store})

@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(request: Request, order_id: int, store = Depends(get_store)):
    """訂單詳情頁"""
    return templates.TemplateResponse(
        request=request, 
        name="customer/order_detail.html", 
        context={"order_id": order_id, "store": store}
    )

# ==================== 後台頁面路由 ====================

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, store = Depends(get_store)):
    """後台登入頁 (已廢棄，導向至統一入口)"""
    return RedirectResponse(url="/shop/admin/login")

@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request, store = Depends(get_store)):
    """後台首頁（重定向到商品管理）"""
    return RedirectResponse(url=f"/shop/{store.slug}/admin/products")

@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products_page(request: Request, store = Depends(get_store)):
    """後台商品管理頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse(request=request, name="admin/products.html", context={"store": store})

@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders_page(request: Request, store = Depends(get_store)):
    """後台訂單管理頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse(request=request, name="admin/orders.html", context={"store": store})

@router.get("/admin/orders/{order_id}", response_class=HTMLResponse)
async def admin_order_detail_page(request: Request, order_id: int, store = Depends(get_store)):
    """後台訂單詳情頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse(
        request=request, 
        name="admin/order_detail.html", 
        context={"order_id": order_id, "store": store}
    )

@router.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories_page(request: Request, store = Depends(get_store)):
    """後台分類管理頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse(request=request, name="admin/categories.html", context={"store": store})

@router.get("/admin/cms", response_class=HTMLResponse)
async def admin_cms_page(request: Request, store = Depends(get_store)):
    """後台商店與首頁設定頁（認證由前端 JavaScript 處理）"""
    return templates.TemplateResponse(request=request, name="admin/cms.html", context={"store": store})
