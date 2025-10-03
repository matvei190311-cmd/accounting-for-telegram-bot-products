import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import Database
from handlers import register_all_handlers


async def main():
    # Инициализация БД (без удаления старой базы)
    db = Database('sqlite:///bot.db')

    # Инициализируем таблицы если их нет
    try:
        db.init_db()
        print("✅ База данных готова")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return

    # Бот
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация обработчиков
    register_all_handlers(dp)
    print("✅ Обработчики зарегистрированы")
    print("🤖 Бот запущен!")

    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())