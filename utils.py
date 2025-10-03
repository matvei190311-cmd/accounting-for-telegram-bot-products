import json
import os
from datetime import datetime, timedelta
from aiogram import types
from config import DEFAULT_LANGUAGE

_locales_cache = {}
_available_languages = []


def load_all_locales():
    """Загружает все доступные локализации из папки locales"""
    global _available_languages
    locales_dir = 'locales'

    if not os.path.exists(locales_dir):
        os.makedirs(locales_dir)
        print(f"⚠️ Создана папка {locales_dir}")
        return

    try:
        locale_files = [f for f in os.listdir(locales_dir) if f.endswith('.json')]
        _available_languages = [f.replace('.json', '') for f in locale_files]

        print(f"✅ Загружены языки: {', '.join(_available_languages)}")

    except Exception as e:
        print(f"❌ Ошибка загрузки локализаций: {e}")
        _available_languages = ['en']  # fallback


def load_locale(language=None):
    if language is None:
        language = DEFAULT_LANGUAGE

    if language in _locales_cache:
        return _locales_cache[language]

    try:
        locale_file = f'locales/{language}.json'
        if not os.path.exists(locale_file):
            # Если файл не найден, пробуем английский как запасной
            if language != 'en':
                print(f"⚠️ Файл локализации {language}.json не найден, используем английский")
                return load_locale('en')
            else:
                return {}

        with open(locale_file, 'r', encoding='utf-8') as f:
            locale_data = json.load(f)
        _locales_cache[language] = locale_data
        return locale_data
    except Exception as e:
        print(f"⚠️ Ошибка загрузки локализации {language}: {e}")
        # Если файл локализации не найден, используем английский как запасной
        if language != 'en':
            return load_locale('en')
        return {}


def get_text(key, language=None, **kwargs):
    if language is None:
        language = DEFAULT_LANGUAGE

    locale = load_locale(language)
    text = locale.get(key, key)  # Если ключ не найден, возвращаем сам ключ

    # Если текст не найден в выбранном языке, пробуем английский
    if text == key and language != 'en':
        en_locale = load_locale('en')
        text = en_locale.get(key, key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            print(f"⚠️ Отсутствует ключ для форматирования: {e} в тексте: {text}")
        except Exception as e:
            print(f"⚠️ Ошибка форматирования текста: {e}")

    return text


def get_available_languages():
    """Возвращает список доступных языков"""
    if not _available_languages:
        load_all_locales()
    return _available_languages


def get_language_keyboard():
    """Динамически создает клавиатуру выбора языка на основе доступных локалей"""
    languages_map = {
        'ru': '🇷🇺 Русский',
        'uz': "🇺🇿 O'zbek",
        'en': '🇺🇸 English',
        'de': '🇩🇪 Deutsch',
        'fr': '🇫🇷 Français',
        'es': '🇪🇸 Español',
        'zh': '🇨🇳 中文',
        'ar': '🇸🇦 العربية',
        'tr': '🇹🇷 Türkçe',
        'ko': '🇰🇷 한국어',
        'ja': '🇯🇵 日本語'
    }

    available_langs = get_available_languages()
    keyboard_buttons = []

    # Создаем строки по 2 кнопки в каждой
    row = []
    for lang_code in available_langs:
        lang_name = languages_map.get(lang_code, f"🌐 {lang_code.upper()}")
        row.append(lang_name)

        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []

    # Добавляем оставшиеся кнопки
    if row:
        keyboard_buttons.append(row)

    return types.ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def format_report(vitrine, balances, transactions, start_date=None, end_date=None, language='uz'):
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    report_texts = {
        'title': get_text('report_for_vitrine', language),
        'period': get_text('period', language),
        'given': get_text('given', language),
        'returned': get_text('returned', language),
        'taken': get_text('taken', language),
        'sold': get_text('sold', language),
        'balance': get_text('balance', language),
        'from_date': get_text('from_date', language),
        'to_date': get_text('to_date', language)
    }

    report = f"{report_texts['title']}: {vitrine.username}\n"
    report += f"{report_texts['period']}: {start_date.strftime('%d.%m.%Y')} {report_texts['from_date']} - {end_date.strftime('%d.%m.%Y')} {report_texts['to_date']}\n\n"

    for balance in balances:
        product = balance.product
        product_transactions = [t for t in transactions if t.product_id == product.id]

        given = sum(t.quantity for t in product_transactions if t.type == 'give' and t.status == 'confirmed')
        returned = sum(t.quantity for t in product_transactions if t.type == 'return' and t.status == 'confirmed')
        taken = sum(t.quantity for t in product_transactions if t.type == 'take' and t.status == 'confirmed')
        sold = sum(t.quantity for t in product_transactions if t.type == 'sale' and t.status == 'confirmed')

        report += f"📦 {product.sku} - {product.name}\n"
        report += f"  {report_texts['given']}: {given}\n"
        report += f"  {report_texts['returned']}: {returned}\n"
        report += f"  {report_texts['taken']}: {taken}\n"
        report += f"  {report_texts['sold']}: {sold}\n"
        report += f"  {report_texts['balance']}: {balance.quantity}\n\n"

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
        print(f"❌ {get_text('message_send_error', 'en')} {chat_id}: {e}")
        return False
    return False


# Загружаем все локализации при импорте модуля
load_all_locales()