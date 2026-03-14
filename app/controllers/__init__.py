from .admin_controller import router as admin_router
from .customer_controller import router as customer_router
from . import page_controller

__all__ = ['admin_router', 'customer_router', 'page_controller']
