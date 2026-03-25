from .admin_controller import router as admin_router
from .customer_controller import router as customer_router
from .page_controller import router as page_router, merchant_router, admin_global_router
from .global_controller import router as global_router

__all__ = ['admin_router', 'customer_router', 'page_router', 'merchant_router', 'global_router', 'admin_global_router']
