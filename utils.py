import json
from datetime import datetime, timedelta
from aiogram import types
from config import DEFAULT_LANGUAGE

_locales_cache = {}


def load_locale(language=None):
    if language is None:
        language = DEFAULT_LANGUAGE

    if language in _locales_cache:
        return _locales_cache[language]

    try:
        locale_file = f'locales/{language}.json'
        with open(locale_file, 'r', encoding='utf-8') as f:
            locale_data = json.load(f)
        _locales_cache[language] = locale_data
        return locale_data
    except FileNotFoundError:
        print(f"⚠️ Файл локализации {language}.json не найден")
        # Если файл локализации не найден, используем русский как запасной
        if language != 'ru':
            return load_locale('ru')
        return {}


def get_text(key, language=None, **kwargs):
    locale = load_locale(language)
    text = locale.get(key, key)  # Если ключ не найден, возвращаем сам ключ

    # Если текст не найден в выбранном языке, пробуем русский
    if text == key and language != 'ru':
        ru_locale = load_locale('ru')
        text = ru_locale.get(key, key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def format_report(vitrine, balances, transactions, start_date=None, end_date=None, language='uz'):
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    report_texts = {
        'ru': {
            'title': "🏪 Отчет для витрины",
            'period': "📅 Период",
            'given': "➕ Отдали",
            'returned': "🔄 Вернули",
            'taken': "➖ Забрал админ",
            'sold': "💰 Продано",
            'balance': "📊 Остаток",
            'from_date': "с",
            'to_date': "по"
        },
        'uz': {
            'title': "🏪 Vitrina hisoboti",
            'period': "📅 Muddat",
            'given': "➕ Berildi",
            'returned': "🔄 Qaytarildi",
            'taken': "➖ Olindi",
            'sold': "💰 Sotildi",
            'balance': "📊 Qoldiq",
            'from_date': "dan",
            'to_date': "gacha"
        }
    }

    texts = report_texts.get(language, report_texts['uz'])

    report = f"{texts['title']}: {vitrine.username}\n"
    report += f"{texts['period']}: {start_date.strftime('%d.%m.%Y')} {texts['from_date']} - {end_date.strftime('%d.%m.%Y')} {texts['to_date']}\n\n"

    for balance in balances:
        product = balance.product
        product_transactions = [t for t in transactions if t.product_id == product.id]

        given = sum(t.quantity for t in product_transactions if t.type == 'give' and t.status == 'confirmed')
        returned = sum(t.quantity for t in product_transactions if t.type == 'return' and t.status == 'confirmed')
        taken = sum(t.quantity for t in product_transactions if t.type == 'take' and t.status == 'confirmed')
        sold = sum(t.quantity for t in product_transactions if t.type == 'sale' and t.status == 'confirmed')

        report += f"📦 {product.sku} - {product.name}\n"
        report += f"  {texts['given']}: {given}\n"
        report += f"  {texts['returned']}: {returned}\n"
        report += f"  {texts['taken']}: {taken}\n"
        report += f"  {texts['sold']}: {sold}\n"
        report += f"  {texts['balance']}: {balance.quantity}\n\n"

    return report


def split_message(text, max_length=4000):
    """Разбивает длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind(' ', 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return parts


async def safe_send_message(bot, chat_id, text, reply_markup=None, max_length=4000):
    """
    Безопасно отправляет сообщение с обработкой ошибок
    """
    try:
        chat = await bot.get_chat(chat_id)
        if chat:
            if len(text) > max_length:
                parts = split_message(text, max_length)
                for part in parts:
                    await bot.send_message(chat_id, part, reply_markup=reply_markup)
                    reply_markup = None
            else:
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
            return True
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения в чат {chat_id}: {e}")
        return False
    return False