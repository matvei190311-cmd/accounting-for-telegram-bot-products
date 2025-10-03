from aiogram import types
from database import Database, Transaction, Balance, User
from keyboards import get_confirmation_reply_keyboard
from utils import safe_send_message
from config import ADMIN_IDS
from logger import log_operation, log_error

db = Database('sqlite:///bot.db')


def get_session():
    return db.get_session()


async def send_confirmation_request(transaction_id, bot):
    """Отправляет запрос на подтверждение операции с reply-кнопками"""
    session = get_session()
    try:
        transaction = session.query(Transaction)    .get(transaction_id)
        if not transaction:
            print(f"❌ Транзакция {transaction_id} не найдена")
            return False

        # Определяем кому отправлять подтверждение
        if transaction.type == 'give':
            target_user = transaction.to_vitrine
            operation_type = "получение товара"
        elif transaction.type == 'return':
            # Для возврата ищем администратора
            if transaction.admin_id:
                target_user = session.query(User).get(transaction.admin_id)
            else:
                # Если admin_id не установлен, ищем первого активного админа
                target_user = session.query(User).filter_by(role='admin').first()
                if target_user:
                    transaction.admin_id = target_user.id
                    session.commit()
            operation_type = "возврат товара"
        elif transaction.type == 'transfer':
            target_user = transaction.to_vitrine
            operation_type = "перемещение товара"
        else:
            return True

        if not target_user:
            print(f"❌ Целевой пользователь не найден для транзакции {transaction_id}")
            return False

        message_text = format_confirmation_message(transaction, operation_type, target_user.language)

        # Используем безопасную отправку
        success = await safe_send_message(
            bot,
            target_user.telegram_id,
            message_text,
            reply_markup=get_confirmation_reply_keyboard(transaction_id, target_user.language)
        )

        if success:
            transaction.needs_confirmation = True
            session.commit()
            print(
                f"✅ Запрос подтверждения отправлен пользователю {target_user.username} (ID: {target_user.telegram_id})")
            return True
        else:
            print(f"❌ Не удалось отправить запрос подтверждения пользователю {target_user.telegram_id}")
            return False

    except Exception as e:
        print(f"❌ Ошибка отправки подтверждения: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def format_confirmation_message(transaction, operation_type, language='uz'):
    """Форматирует сообщение для подтверждения"""
    product = transaction.product

    if transaction.type == 'give':
        from_user = transaction.admin
        if language == 'ru':
            message = (
                f"📦 ЗАПРОС НА ПОЛУЧЕНИЕ ТОВАРА\n\n"
                f"Администратор {from_user.username} отправляет вам товар:\n"
                f"📦 Товар: {product.name}\n"
                f"🔢 Количество: {transaction.quantity} шт.\n\n"
                f"Подтвердите получение:"
            )
        else:
            message = (
                f"📦 MAHSULOT OLISH SO'ROVI\n\n"
                f"Administrator {from_user.username} sizga mahsulot yubormoqda:\n"
                f"📦 Mahsulot: {product.name}\n"
                f"🔢 Miqdor: {transaction.quantity} dona\n\n"
                f"Olishni tasdiqlang:"
            )

    elif transaction.type == 'return':
        from_user = transaction.from_vitrine
        if language == 'ru':
            message = (
                f"🔄 ЗАПРОС НА ВОЗВРАТ ТОВАРА\n\n"
                f"Витрина {from_user.username} возвращает товар:\n"
                f"📦 Товар: {product.name}\n"
                f"🔢 Количество: {transaction.quantity} шт.\n\n"
                f"Подтвердите возврат:"
            )
        else:
            message = (
                f"🔄 MAHSULOT QAYTARISH SO'ROVI\n\n"
                f"Vitrina {from_user.username} mahsulotni qaytarmoqda:\n"
                f"📦 Mahsulot: {product.name}\n"
                f"🔢 Miqdor: {transaction.quantity} dona\n\n"
                f"Qaytarishni tasdiqlang:"
            )

    elif transaction.type == 'transfer':
        from_user = transaction.from_vitrine
        if language == 'ru':
            message = (
                f"🔄 ЗАПРОС НА ПЕРЕМЕЩЕНИЕ ТОВАРА\n\n"
                f"Товар перемещается от {from_user.username} к вам:\n"
                f"📦 Товар: {product.name}\n"
                f"🔢 Количество: {transaction.quantity} шт.\n\n"
                f"Подтвердите получение:"
            )
        else:
            message = (
                f"🔄 MAHSULOT KO'CHIRISH SO'ROVI\n\n"
                f"Mahsulot {from_user.username} dan sizga ko'chirilmoqda:\n"
                f"📦 Mahsulot: {product.name}\n"
                f"🔢 Miqdor: {transaction.quantity} dona\n\n"
                f"Olishni tasdiqlang:"
            )

    return message


async def process_confirmation_reply(message: types.Message, confirm: bool):
    """Обрабатывает подтверждение/отклонение операции из reply-кнопок"""
    session = get_session()
    try:
        # Извлекаем ID транзакции из текста кнопки
        text = message.text
        if "✅ Подтвердить_" in text or "✅ Tasdiqlash_" in text:
            transaction_id = int(text.split("_")[1])
        elif "❌ Отклонить_" in text or "❌ Rad etish_" in text:
            transaction_id = int(text.split("_")[1])
        else:
            return False

        transaction = session.query(Transaction).get(transaction_id)
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if not transaction or transaction.status != 'pending':
            await message.answer("Операция уже обработана!")
            return True

        if confirm:
            transaction.status = 'confirmed'
            transaction.confirmed_by = user.id
            await update_balances(transaction, session)
            await send_confirmation_notification(transaction, True, message.bot)

            # Логируем подтверждение
            log_operation(transaction.id, f'{transaction.type}_confirmed',
                          f"Подтверждено пользователем {user.username}")

            await message.answer("✅ Операция подтверждена!", reply_markup=types.ReplyKeyboardRemove())
        else:
            transaction.status = 'rejected'
            await send_confirmation_notification(transaction, False, message.bot)

            # Логируем отклонение
            log_operation(transaction.id, f'{transaction.type}_rejected',
                          f"Отклонено пользователем {user.username}")

            await message.answer("❌ Операция отклонена!", reply_markup=types.ReplyKeyboardRemove())

        session.commit()
        return True

    except Exception as e:
        log_error('confirmation_processing', str(e), message.from_user.id)
        print(f"❌ Ошибка обработки подтверждения: {e}")
        session.rollback()
        await message.answer("Произошла ошибка!", reply_markup=types.ReplyKeyboardRemove())
        return False
    finally:
        session.close()


async def send_confirmation_notification(transaction, confirmed, bot):
    """Отправляет уведомление о результате подтверждения"""
    try:
        if transaction.type == 'give':
            target_user = transaction.admin
            if confirmed:
                message = f"✅ Витрина подтвердила получение товара:\n{transaction.product.name} - {transaction.quantity} шт."
            else:
                message = f"❌ Витрина отклонила получение товара:\n{transaction.product.name} - {transaction.quantity} шт."

        elif transaction.type == 'return':
            target_user = transaction.from_vitrine
            if confirmed:
                message = f"✅ Админ подтвердил возврат товара:\n{transaction.product.name} - {transaction.quantity} шт."
            else:
                message = f"❌ Админ отклонил возврат товара:\n{transaction.product.name} - {transaction.quantity} шт."

        elif transaction.type == 'transfer':
            target_user = transaction.from_vitrine
            if confirmed:
                message = f"✅ Получатель подтвердил получение товара:\n{transaction.product.name} - {transaction.quantity} шт."
            else:
                message = f"❌ Получатель отклонил получение товара:\n{transaction.product.name} - {transaction.quantity} шт."

        if target_user:
            # Используем безопасную отправку
            await safe_send_message(bot, target_user.telegram_id, message)

    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")

