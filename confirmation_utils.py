from aiogram import types
from database import Database, Transaction, Balance, User
from keyboards import get_confirmation_reply_keyboard
from utils import safe_send_message, get_text
from config import ADMIN_IDS
from logger import log_operation, log_error

db = Database('sqlite:///bot.db')


def get_session():
    return db.get_session()


async def update_balances(transaction, session):
    """Обновляет балансы после подтверждения операции"""
    try:
        if transaction.type == 'give':
            # Обновляем баланс получателя
            balance = session.query(Balance).filter_by(
                vitrine_id=transaction.to_vitrine_id,
                product_id=transaction.product_id
            ).first()

            if not balance:
                balance = Balance(
                    vitrine_id=transaction.to_vitrine_id,
                    product_id=transaction.product_id,
                    quantity=transaction.quantity
                )
                session.add(balance)
            else:
                balance.quantity += transaction.quantity

        elif transaction.type == 'return':
            # Уменьшаем баланс витрины
            balance = session.query(Balance).filter_by(
                vitrine_id=transaction.from_vitrine_id,
                product_id=transaction.product_id
            ).first()

            if balance and balance.quantity >= transaction.quantity:
                balance.quantity -= transaction.quantity
            else:
                raise Exception(get_text('not_enough_products', 'en'))

        elif transaction.type == 'transfer':
            # Уменьшаем баланс отправителя, увеличиваем баланс получателя
            from_balance = session.query(Balance).filter_by(
                vitrine_id=transaction.from_vitrine_id,
                product_id=transaction.product_id
            ).first()

            if not from_balance or from_balance.quantity < transaction.quantity:
                raise Exception(get_text('not_enough_products', 'en'))

            from_balance.quantity -= transaction.quantity

            to_balance = session.query(Balance).filter_by(
                vitrine_id=transaction.to_vitrine_id,
                product_id=transaction.product_id
            ).first()

            if not to_balance:
                to_balance = Balance(
                    vitrine_id=transaction.to_vitrine_id,
                    product_id=transaction.product_id,
                    quantity=transaction.quantity
                )
                session.add(to_balance)
            else:
                to_balance.quantity += transaction.quantity

        session.commit()

    except Exception as e:
        session.rollback()
        raise e


async def send_confirmation_request(transaction_id, bot):
    """Отправляет запрос на подтверждение операции с reply-кнопками"""
    session = get_session()
    try:
        transaction = session.query(Transaction).get(transaction_id)
        if not transaction:
            print(f"❌ {get_text('transaction_not_found', 'en')} {transaction_id}")
            return False

        # Определяем кому отправлять подтверждение
        if transaction.type == 'give':
            target_user = transaction.to_vitrine
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
        elif transaction.type == 'transfer':
            target_user = transaction.to_vitrine
        else:
            return True

        if not target_user:
            print(f"❌ {get_text('target_user_not_found', 'en')} {transaction_id}")
            return False

        message_text = format_confirmation_message(transaction, target_user.language)

        # Используем безопасную отправку с динамической клавиатурой
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
                f"✅ {get_text('confirmation_request_sent', 'en')} {target_user.username} (ID: {target_user.telegram_id})")
            return True
        else:
            print(f"❌ {get_text('confirmation_send_error', 'en')} {target_user.telegram_id}")
            return False

    except Exception as e:
        print(f"❌ {get_text('confirmation_error', 'en')}: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def format_confirmation_message(transaction, language='en'):
    """Форматирует сообщение для подтверждения"""
    product = transaction.product

    if transaction.type == 'give':
        from_user = transaction.admin
        message = (
            f"📦 {get_text('give_request_title', language)}\n\n"
            f"{get_text('admin', language)} {from_user.username} {get_text('sending_product', language)}:\n"
            f"📦 {get_text('product', language)}: {product.name}\n"
            f"🔢 {get_text('quantity', language)}: {transaction.quantity} {get_text('pcs', language)}\n\n"
            f"{get_text('confirm_receipt', language)}:"
        )

    elif transaction.type == 'return':
        from_user = transaction.from_vitrine
        message = (
            f"🔄 {get_text('return_request_title', language)}\n\n"
            f"{get_text('vitrines', language)} {from_user.username} {get_text('returning_product', language)}:\n"
            f"📦 {get_text('product', language)}: {product.name}\n"
            f"🔢 {get_text('quantity', language)}: {transaction.quantity} {get_text('pcs', language)}\n\n"
            f"{get_text('confirm_return', language)}:"
        )

    elif transaction.type == 'transfer':
        from_user = transaction.from_vitrine
        message = (
            f"🔄 {get_text('transfer_request_title', language)}\n\n"
            f"{get_text('product_transfer_from', language)} {from_user.username} {get_text('to_you', language)}:\n"
            f"📦 {get_text('product', language)}: {product.name}\n"
            f"🔢 {get_text('quantity', language)}: {transaction.quantity} {get_text('pcs', language)}\n\n"
            f"{get_text('confirm_receipt', language)}:"
        )

    return message


async def process_confirmation_reply(message: types.Message, confirm: bool, transaction_id: int = None):
    """Обрабатывает подтверждение/отклонение операции из reply-кнопок"""
    session = get_session()
    try:
        # Если transaction_id не передан, пытаемся извлечь из текста
        if transaction_id is None:
            text = message.text
            # Пытаемся извлечь ID из текста (последний элемент после разделения по _)
            try:
                transaction_id = int(text.split("_")[-1])
            except (IndexError, ValueError):
                print(f"❌ Не удалось извлечь ID транзакции из текста: {text}")
                return False

        transaction = session.query(Transaction).get(transaction_id)
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        user_language = user.language if user else 'en'

        if not transaction or transaction.status != 'pending':
            await message.answer(get_text('already_processed', user_language))
            return True

        if confirm:
            transaction.status = 'confirmed'
            transaction.confirmed_by = user.id
            await update_balances(transaction, session)
            await send_confirmation_notification(transaction, True, message.bot)

            # Логируем подтверждение
            log_operation(transaction.id, f'{transaction.type}_confirmed',
                          f"{get_text('confirmed_by_user', 'en')} {user.username}")

            await message.answer(get_text('operation_confirmed', user_language),
                                 reply_markup=types.ReplyKeyboardRemove())
        else:
            transaction.status = 'rejected'
            await send_confirmation_notification(transaction, False, message.bot)

            # Логируем отклонение
            log_operation(transaction.id, f'{transaction.type}_rejected',
                          f"{get_text('rejected_by_user', 'en')} {user.username}")

            await message.answer(get_text('operation_rejected', user_language),
                                 reply_markup=types.ReplyKeyboardRemove())

        session.commit()
        return True

    except Exception as e:
        log_error('confirmation_processing', str(e), message.from_user.id)
        print(f"❌ {get_text('confirmation_processing_error', 'en')}: {e}")
        session.rollback()
        await message.answer(get_text('error_occurred', 'en'), reply_markup=types.ReplyKeyboardRemove())
        return False
    finally:
        session.close()


async def send_confirmation_notification(transaction, confirmed, bot):
    """Отправляет уведомление о результате подтверждения с полной динамической локализацией"""
    try:
        session = get_session()

        # Определяем целевого пользователя и тип сообщения
        if transaction.type == 'give':
            target_user = transaction.admin
            if confirmed:
                message_key = 'give_confirmed_notification'
            else:
                message_key = 'give_rejected_notification'

        elif transaction.type == 'return':
            target_user = transaction.from_vitrine
            if confirmed:
                message_key = 'return_confirmed_notification'
            else:
                message_key = 'return_rejected_notification'

        elif transaction.type == 'transfer':
            target_user = transaction.from_vitrine
            if confirmed:
                message_key = 'transfer_confirmed_notification'
            else:
                message_key = 'transfer_rejected_notification'
        else:
            session.close()
            return

        if target_user:
            # Получаем язык пользователя
            user_language = target_user.language if target_user.language else 'en'

            # Формируем сообщение с динамической локализацией
            product_info = f"\n📦 {transaction.product.name} - {transaction.quantity} {get_text('pcs', user_language)}"

            if confirmed:
                status_emoji = "✅"
                base_message = get_text(message_key, user_language)
            else:
                status_emoji = "❌"
                base_message = get_text(message_key, user_language)

            message = f"{status_emoji} {base_message}{product_info}"

            # Используем безопасную отправку
            await safe_send_message(bot, target_user.telegram_id, message)

        session.close()

    except Exception as e:
        print(f"❌ {get_text('notification_send_error', 'en')}: {e}")