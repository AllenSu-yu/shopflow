from .auth_service import (
    register_customer,
    authenticate_customer,
    authenticate_admin
)
from .product_service import (
    get_products,
    get_product_by_id,
    search_products,
    create_product,
    update_product,
    delete_product
)
from .cart_service import (
    get_or_create_cart,
    add_to_cart,
    add_to_cart_batch,
    update_cart_item,
    remove_from_cart,
    clear_cart,
    get_cart_total,
    get_cart_details
)
from .order_service import (
    create_order,
    get_orders_by_customer,
    get_order_by_id,
    update_order_status,
    generate_order_number
)
from .cms_service import (
    get_carousels,
    get_carousel_by_id,
    create_carousel,
    update_carousel,
    delete_carousel,
    get_store_info,
    update_store_info
)

__all__ = [
    # Auth service
    'register_customer',
    'authenticate_customer',
    'authenticate_admin',
    # Product service
    'get_products',
    'get_product_by_id',
    'search_products',
    'create_product',
    'update_product',
    'delete_product',
    # Cart service
    'get_or_create_cart',
    'add_to_cart',
    'add_to_cart_batch',
    'update_cart_item',
    'remove_from_cart',
    'clear_cart',
    'get_cart_total',
    'get_cart_details',
    # Order service
    'create_order',
    'get_orders_by_customer',
    'get_order_by_id',
    'update_order_status',
    'generate_order_number',
    # CMS service
    'get_carousels',
    'get_carousel_by_id',
    'create_carousel',
    'update_carousel',
    'delete_carousel',
    'get_store_info',
    'update_store_info',
]
