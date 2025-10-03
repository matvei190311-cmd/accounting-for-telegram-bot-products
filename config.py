import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

ADMIN_IDS = []
admin_ids_str = os.getenv('ADMIN_IDS', '')
if admin_ids_str:
    try:
        ADMIN_IDS = list(map(int, admin_ids_str.split(',')))
    except ValueError:
        print("⚠️ Ошибка в формате ADMIN_IDS")

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'uz')
VITRINE_PASSWORD = os.getenv('VITRINE_PASSWORD', 'vitrine123')

print(f"✅ BOT_TOKEN загружен")
print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
print(f"✅ DEFAULT_LANGUAGE: {DEFAULT_LANGUAGE}")