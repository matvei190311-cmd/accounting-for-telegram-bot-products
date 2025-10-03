"""
Файл для импортов обработчиков, чтобы избежать циклических импортов
"""

# Импорты будут выполнены позже, когда модули уже загружены
admin_handlers = None
vitrine_handlers = None
admin_state_handlers = None

def init_handlers():
    """Инициализирует обработчики после загрузки всех модулей"""
    global admin_handlers, vitrine_handlers, admin_state_handlers

    from .admin import (
        admin_products_handler, admin_vitrines_handler, admin_reports_handler,
        admin_operations_handler, admin_take_product_handler, admin_transfer_handler,
        select_vitrine_handler, select_product_handler, enter_quantity_handler,
        take_select_vitrine_handler, take_select_product_handler, take_enter_quantity_handler,
        transfer_select_from_vitrine_handler, transfer_select_product_handler,
        transfer_select_to_vitrine_handler, transfer_enter_quantity_handler,
        operations_menu_handler
    )

    from .vitrine import (
        vitrine_products_handler, vitrine_returns_handler,
        vitrine_sales_handler, vitrine_reports_handler,
        select_return_product_handler, enter_return_quantity_handler,
        select_sale_product_handler, enter_sale_quantity_handler
    )

    admin_handlers = {
        'products': admin_products_handler,
        'vitrines': admin_vitrines_handler,
        'reports': admin_reports_handler,
        'operations': admin_operations_handler,
        'take_product': admin_take_product_handler,
        'transfer': admin_transfer_handler
    }

    vitrine_handlers = {
        'products': vitrine_products_handler,
        'returns': vitrine_returns_handler,
        'sales': vitrine_sales_handler,
        'reports': vitrine_reports_handler
    }

    admin_state_handlers = {
        'select_vitrine': select_vitrine_handler,
        'select_product': select_product_handler,
        'enter_quantity': enter_quantity_handler,
        'take_select_vitrine': take_select_vitrine_handler,
        'take_select_product': take_select_product_handler,
        'take_enter_quantity': take_enter_quantity_handler,
        'transfer_select_from_vitrine': transfer_select_from_vitrine_handler,
        'transfer_select_product': transfer_select_product_handler,
        'transfer_select_to_vitrine': transfer_select_to_vitrine_handler,
        'transfer_enter_quantity': transfer_enter_quantity_handler,
        'operations_menu': operations_menu_handler
    }

def get_admin_handler(key):
    """Возвращает обработчик администратора по ключу"""
    if admin_handlers is None:
        init_handlers()
    return admin_handlers.get(key)

def get_vitrine_handler(key):
    """Возвращает обработчик витрины по ключу"""
    if vitrine_handlers is None:
        init_handlers()
    return vitrine_handlers.get(key)

def get_admin_state_handler(key):
    """Возвращает обработчик состояния администратора по ключу"""
    if admin_state_handlers is None:
        init_handlers()
    return admin_state_handlers.get(key)