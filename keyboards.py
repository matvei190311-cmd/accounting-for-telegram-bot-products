from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_text


def get_language_keyboard():
    """Клавиатура выбора языка"""
    return ReplyKeyboardMarkup([
        ["🇷🇺 Русский", "🇺🇿 O'zbek"]
    ], resize_keyboard=True)


def get_main_keyboard(role, language='uz'):
    """Главное меню"""
    if role == 'admin':
        return ReplyKeyboardMarkup([
            [KeyboardButton(get_text('products', language)), KeyboardButton(get_text('vitrines', language))],
            [KeyboardButton(get_text('take_product', language)), KeyboardButton(get_text('transfer', language))],
            [KeyboardButton(get_text('reports', language)), KeyboardButton(get_text('operations', language))],
            [KeyboardButton(get_text('back_to_main', language))]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton(get_text('products', language)), KeyboardButton(get_text('returns', language))],
            [KeyboardButton(get_text('sales', language)), KeyboardButton(get_text('reports', language))],
            [KeyboardButton(get_text('back_to_main', language))]
        ], resize_keyboard=True)


def get_products_keyboard(products, language='uz'):
    """Клавиатура выбора товара"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for product in products:
        keyboard.add(KeyboardButton(f"📦 {product.name}"))
    keyboard.add(KeyboardButton(get_text('back_to_main', language)))
    return keyboard


def get_quantity_input_keyboard(language='uz'):
    """Клавиатура только с кнопкой возврата (для ввода количества)"""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_text('back_to_main', language))]
    ], resize_keyboard=True)


def get_vitrines_keyboard(vitrines, language='uz'):
    """Клавиатура выбора витрины"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for vitrine in vitrines:
        keyboard.add(KeyboardButton(f"🏪 {vitrine.username}"))
    keyboard.add(KeyboardButton(get_text('back_to_main', language)))
    return keyboard


def get_confirmation_reply_keyboard(transaction_id, language='uz'):
    """Клавиатура подтверждения с reply-кнопками"""
    return ReplyKeyboardMarkup([
        [
            KeyboardButton(f"✅ {get_text('confirm', language)}_{transaction_id}"),
            KeyboardButton(f"❌ {get_text('reject', language)}_{transaction_id}")
        ],
        [KeyboardButton(get_text('back_to_main', language))]
    ], resize_keyboard=True)


def get_operations_period_keyboard(language='uz'):
    """Клавиатура выбора периода для операций"""
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_text('all_operations', language)), KeyboardButton(get_text('today', language))],
        [KeyboardButton(get_text('week', language)), KeyboardButton(get_text('month', language))],
        [KeyboardButton(get_text('export_csv', language)), KeyboardButton(get_text('back_to_main', language))]
    ], resize_keyboard=True)



def get_report_types_keyboard(language='uz'):
    """Клавиатура типов отчетов"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Umumiy hisobot / Общий отчет"), KeyboardButton("📈 Detal hisobot / Детальный отчет")],
        [KeyboardButton("🕐 Kunlik hisobot / Ежедневный отчет"), KeyboardButton("📅 Oylik hisobot / Месячный отчет")],
        [KeyboardButton(get_text('back_to_main', language))]
    ], resize_keyboard=True)


















