from .common import register_common_handlers

def register_all_handlers(dp):
    register_common_handlers(dp)
    print("✅ Все обработчики зарегистрированы (динамическая система)")

__all__ = ['register_all_handlers']