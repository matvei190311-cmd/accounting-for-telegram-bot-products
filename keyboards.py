from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_text, get_available_languages


def get_main_keyboard(role, language='en'):
    """Главное меню - динамически создается на основе языка"""
    if role == 'admin':
        return ReplyKeyboardMarkup([
            [
                KeyboardButton(get_text('products', language)),
                KeyboardButton(get_text('vitrines', language))
            ],
            [
                KeyboardButton(get_text('take_product', language)),
                KeyboardButton(get_text('transfer', language))
            ],
            [
                KeyboardButton(get_text('reports', language)),
                KeyboardButton(get_text('operations', language))
            ],
            [
                KeyboardButton(get_text('change_language', language)),
                KeyboardButton(get_text('back_to_main', language))
            ]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [
                KeyboardButton(get_text('products', language)),
                KeyboardButton(get_text('returns', language))
            ],
            [
                KeyboardButton(get_text('sales', language)),
                KeyboardButton(get_text('reports', language))
            ],
            [
                KeyboardButton(get_text('change_language', language)),
                KeyboardButton(get_text('back_to_main', language))
            ]
        ], resize_keyboard=True)


def get_products_keyboard(products, language='en'):
    """Клавиатура выбора товара"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for product in products:
        keyboard.add(KeyboardButton(f"📦 {product.name}"))
    keyboard.add(KeyboardButton(get_text('back_to_main', language)))
    return keyboard


def get_quantity_input_keyboard(language='en'):
    """Клавиатура только с кнопкой возврата (для ввода количества)"""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_text('back_to_main', language))]
    ], resize_keyboard=True)


def get_vitrines_keyboard(vitrines, language='en'):
    """Клавиатура выбора витрины"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for vitrine in vitrines:
        keyboard.add(KeyboardButton(f"🏪 {vitrine.username}"))
    keyboard.add(KeyboardButton(get_text('back_to_main', language)))
    return keyboard


def get_confirmation_reply_keyboard(transaction_id, language='en'):
    """Клавиатура подтверждения с reply-кнопками - динамически создается"""
    confirm_text = get_text('confirm', language)
    reject_text = get_text('reject', language)

    return ReplyKeyboardMarkup([
        [
            KeyboardButton(f"✅ {confirm_text}_{transaction_id}"),
            KeyboardButton(f"❌ {reject_text}_{transaction_id}")
        ],
        [KeyboardButton(get_text('back_to_main', language))]
    ], resize_keyboard=True)


def get_operations_period_keyboard(language='en'):
    """Клавиатура выбора периода для операций"""
    return ReplyKeyboardMarkup([
        [
            KeyboardButton(get_text('all_operations', language)),
            KeyboardButton(get_text('today', language))
        ],
        [
            KeyboardButton(get_text('week', language)),
            KeyboardButton(get_text('month', language))
        ],
        [
            KeyboardButton(get_text('export_csv', language)),
            KeyboardButton(get_text('back_to_main', language))
        ]
    ], resize_keyboard=True)


def generate_confirmation_patterns():
    """Генерирует паттерны для кнопок подтверждения для всех языков"""
    patterns = []
    available_languages = get_available_languages()

    for lang_code in available_languages:
        confirm_text = get_text('confirm', lang_code)
        reject_text = get_text('reject', lang_code)

        if confirm_text:
            patterns.append(f"✅ {confirm_text}_")
        if reject_text:
            patterns.append(f"❌ {reject_text}_")

    return patterns


def generate_menu_patterns():
    """Генерирует паттерны для всех кнопок меню для всех языков"""
    patterns = []
    available_languages = get_available_languages()

    # Список всех ключей кнопок меню
    menu_keys = [
        'products', 'vitrines', 'reports', 'operations',
        'take_product', 'transfer', 'returns', 'sales',
        'change_language'
    ]

    for lang_code in available_languages:
        for key in menu_keys:
            menu_text = get_text(key, lang_code)
            if menu_text and menu_text not in patterns:
                patterns.append(menu_text)

    return patterns


def get_menu_button_texts():
    """Возвращает тексты всех кнопок меню для всех языков"""
    menu_texts = {}
    available_languages = get_available_languages()

    menu_keys = [
        'products', 'vitrines', 'reports', 'operations',
        'take_product', 'transfer', 'returns', 'sales'
    ]

    for lang_code in available_languages:
        menu_texts[lang_code] = {}
        for key in menu_keys:
            menu_texts[lang_code][key] = get_text(key, lang_code)

    return menu_texts


def get_confirmation_button_texts():
    """Возвращает тексты кнопок подтверждения для всех языков"""
    confirm_texts = {}
    reject_texts = {}
    available_languages = get_available_languages()

    for lang_code in available_languages:
        confirm_texts[lang_code] = get_text('confirm', lang_code)
        reject_texts[lang_code] = get_text('reject', lang_code)

    return confirm_texts, reject_texts