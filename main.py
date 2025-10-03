import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import Database
from handlers import register_all_handlers
from utils import load_all_locales  # Добавляем импорт


async def main():
    # Загружаем все локализации при запуске
    load_all_locales()

    # Инициализация БД
    db = Database('sqlite:///bot.db')

    # Инициализируем таблицы если их нет
    try:
        db.init_db()
        print("✅ Database ready")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return

    # Бот
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация обработчиков
    register_all_handlers(dp)
    print("✅ Handlers registered")
    print("🤖 Bot started!")

    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())