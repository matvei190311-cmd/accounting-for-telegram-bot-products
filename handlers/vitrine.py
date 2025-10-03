from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import Database, User, Product, Transaction, Balance
from keyboards import get_products_keyboard, get_main_keyboard, get_quantity_input_keyboard
from states import VitrineStates
from utils import get_text, format_report, safe_send_message
from confirmation_utils import send_confirmation_request
from config import ADMIN_IDS
from datetime import datetime, timedelta
from logger import log_operation, log_error

db = Database('sqlite:///bot.db')


def get_session():
    return db.get_session()


# 📦 ТОВАРЫ ВИТРИНЫ
async def vitrine_products_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        balances = session.query(Balance).filter_by(vitrine_id=user.id).all()

        if balances:
            text = get_text('my_products', user.language)
            for balance in balances:
                text += f"📦 {balance.product.name}\n"
                text += f"  🔢 {get_text('available', user.language)}: {balance.quantity} {get_text('pcs', user.language)}\n"
                text += f"  🆔 SKU: {balance.product.sku}\n\n"
            await message.answer(text)
        else:
            await message.answer(get_text('no_products', user.language))

    except Exception as e:
        print(f"❌ Ошибка в vitrine_products_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


# 2. 🔄 ВОЗВРАТ ТОВАРА (требует подтверждения админом)
async def vitrine_returns_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        balances = session.query(Balance).filter_by(vitrine_id=user.id).filter(Balance.quantity > 0).all()

        if balances:
            products = [balance.product for balance in balances]
            await message.answer(
                get_text('start_return', user.language),
                reply_markup=get_products_keyboard(products, user.language)
            )
            await VitrineStates.select_return_product.set()
        else:
            await message.answer(get_text('no_products_for_return', user.language))

    except Exception as e:
        print(f"❌ Ошибка в vitrine_returns_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def select_return_product_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('vitrine', user.language))
            await VitrineStates.menu.set()
            return

        product_name = message.text.replace("📦 ", "")
        product = session.query(Product).filter_by(name=product_name).first()

        if product:
            await state.update_data(return_product_id=product.id)

            # Показываем текущий остаток
            balance = session.query(Balance).filter_by(
                vitrine_id=user.id,
                product_id=product.id
            ).first()
            current_quantity = balance.quantity if balance else 0

            await message.answer(
                f"🔄 {get_text('returns', user.language)}: {product.name}\n"
                f"📊 {get_text('available', user.language)}: {current_quantity} {get_text('pcs', user.language)}\n\n"
                f"{get_text('return_quantity', user.language)} (1 {get_text('from_date', user.language)} {current_quantity}):",
                reply_markup=get_quantity_input_keyboard(user.language)
            )
            await VitrineStates.enter_return_quantity.set()
        else:
            await message.answer(get_text('product_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в select_return_product_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def enter_return_quantity_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('vitrine', user.language))
            await VitrineStates.menu.set()
            return

        try:
            quantity = int(message.text)
        except ValueError:
            await message.answer(get_text('quantity_error', user.language))
            return

        if quantity <= 0:
            await message.answer(get_text('quantity_positive_error', user.language))
            return

        if quantity > 10000:
            await message.answer(get_text('quantity_max_error', user.language))
            return

        data = await state.get_data()
        balance = session.query(Balance).filter_by(
            vitrine_id=user.id,
            product_id=data['return_product_id']
        ).first()

        if not balance:
            await message.answer(get_text('product_not_found', user.language))
            return

        if balance.quantity < quantity:
            await message.answer(
                f"❌ {get_text('not_enough_products', user.language)}!\n"
                f"📦 {get_text('products', user.language)}: {balance.product.name}\n"
                f"📊 {get_text('available', user.language)}: {balance.quantity} {get_text('pcs', user.language)}\n"
                f"🔄 {get_text('requested', user.language)}: {quantity} {get_text('pcs', user.language)}\n\n"
                f"{get_text('enter_quantity', user.language)}:"
            )
            return

        # Создаем транзакцию возврата
        transaction = Transaction(
            type='return',
            product_id=data['return_product_id'],
            quantity=quantity,
            from_vitrine_id=user.id,
            status='pending',
            needs_confirmation=True
        )
        session.add(transaction)
        session.commit()

        product = session.query(Product).get(data['return_product_id'])

        # Логируем создание возврата
        log_operation(transaction.id, 'return_created',
                      f"Витрина {user.username} создала запрос на возврат")

        # Находим активных администраторов
        active_admins = []
        for admin_id in ADMIN_IDS:
            admin_user = session.query(User).filter_by(telegram_id=admin_id, role='admin').first()
            if admin_user:
                active_admins.append(admin_user)

        # Если нет активных админов в базе, создаем временную запись
        if not active_admins:
            for admin_id in ADMIN_IDS:
                temp_admin = User(
                    telegram_id=admin_id,
                    username=f"admin_{admin_id}",
                    role='admin',
                    language='ru'
                )
                try:
                    session.add(temp_admin)
                    session.commit()
                    active_admins.append(temp_admin)
                    print(f"✅ Создан временный администратор для ID {admin_id}")
                except Exception as e:
                    session.rollback()
                    print(f"⚠️ Не удалось создать временного администратора для ID {admin_id}: {e}")

        # Отправляем запрос подтверждения первому доступному администратору
        confirmation_sent = False
        for admin in active_admins:
            transaction.admin_id = admin.id
            session.commit()

            confirmation_sent = await send_confirmation_request(transaction.id, message.bot)
            if confirmation_sent:
                log_operation(transaction.id, 'return_request_sent',
                              f"Запрос отправлен администратору {admin.username}")
                break

        if confirmation_sent:
            await message.answer(
                f"🔄 {get_text('confirmation_request_sent', user.language)}\n"
                f"📦 {get_text('products', user.language)}: {product.name}\n"
                f"🔢 {get_text('quantity', user.language)}: {quantity} {get_text('pcs', user.language)}\n\n"
                f"⏳ {get_text('waiting_confirmation', user.language)}",
                reply_markup=get_main_keyboard('vitrine', user.language)
            )
        else:
            session.delete(transaction)
            session.commit()
            log_error('return_creation', 'Не удалось отправить запрос подтверждения', user.telegram_id)
            await message.answer(
                get_text('admins_unavailable', user.language),
                reply_markup=get_main_keyboard('vitrine', user.language)
            )

        await VitrineStates.menu.set()

    except Exception as e:
        log_error('return_creation', str(e), message.from_user.id)
        print(f"❌ Ошибка в enter_return_quantity_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
        session.rollback()
    finally:
        session.close()


# 4. 💰 ПРОДАЖА ТОВАРА (не требует подтверждения)
async def vitrine_sales_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        balances = session.query(Balance).filter_by(vitrine_id=user.id).filter(Balance.quantity > 0).all()

        if balances:
            products = [balance.product for balance in balances]
            await message.answer(
                get_text('sales', user.language),
                reply_markup=get_products_keyboard(products, user.language)
            )
            await VitrineStates.select_sale_product.set()
        else:
            await message.answer(get_text('no_products_for_sale', user.language))

    except Exception as e:
        print(f"❌ Ошибка в vitrine_sales_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def select_sale_product_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('vitrine', user.language))
            await VitrineStates.menu.set()
            return

        product_name = message.text.replace("📦 ", "")
        product = session.query(Product).filter_by(name=product_name).first()

        if product:
            await state.update_data(sale_product_id=product.id)

            balance = session.query(Balance).filter_by(
                vitrine_id=user.id,
                product_id=product.id
            ).first()
            current_quantity = balance.quantity if balance else 0

            await message.answer(
                f"💰 {get_text('sales', user.language)}: {product.name}\n"
                f"📊 {get_text('available', user.language)}: {current_quantity} {get_text('pcs', user.language)}\n\n"
                f"{get_text('enter_quantity', user.language)} (1 {get_text('from_date', user.language)} {current_quantity}):",
                reply_markup=get_quantity_input_keyboard(user.language)
            )
            await VitrineStates.enter_sale_quantity.set()
        else:
            await message.answer(get_text('product_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в select_sale_product_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def enter_sale_quantity_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('vitrine', user.language))
            await VitrineStates.menu.set()
            return

        try:
            quantity = int(message.text)
        except ValueError:
            await message.answer(get_text('quantity_error', user.language))
            return

        if quantity <= 0:
            await message.answer(get_text('quantity_positive_error', user.language))
            return

        if quantity > 10000:
            await message.answer(get_text('quantity_max_error', user.language))
            return

        data = await state.get_data()
        balance = session.query(Balance).filter_by(
            vitrine_id=user.id,
            product_id=data['sale_product_id']
        ).first()

        if not balance:
            await message.answer(get_text('product_not_found', user.language))
            return

        if balance.quantity < quantity:
            await message.answer(
                f"❌ {get_text('not_enough_products', user.language)}!\n"
                f"📦 {get_text('products', user.language)}: {balance.product.name}\n"
                f"📊 {get_text('available', user.language)}: {balance.quantity} {get_text('pcs', user.language)}\n"
                f"🔄 {get_text('requested', user.language)}: {quantity} {get_text('pcs', user.language)}\n\n"
                f"{get_text('enter_quantity', user.language)}:"
            )
            return

        transaction = Transaction(
            type='sale',
            product_id=data['sale_product_id'],
            quantity=quantity,
            from_vitrine_id=user.id,
            status='confirmed'
        )
        session.add(transaction)
        balance.quantity -= quantity
        session.commit()

        product = session.query(Product).get(data['sale_product_id'])

        # Логируем продажу
        log_operation(transaction.id, 'sale_completed',
                      f"Витрина {user.username} продала товар")

        await message.answer(
            f"✅ {get_text('sale_registered', user.language)}\n"
            f"📦 {get_text('products', user.language)}: {product.name}\n"
            f"💰 {get_text('sold', user.language)}: {quantity} {get_text('pcs', user.language)}\n"
            f"📊 {get_text('new_balance', user.language)}: {balance.quantity} {get_text('pcs', user.language)}",
            reply_markup=get_main_keyboard('vitrine', user.language)
        )

        # ДИНАМИЧЕСКАЯ ЛОКАЛИЗАЦИЯ УВЕДОМЛЕНИЙ ДЛЯ АДМИНИСТРАТОРОВ
        notification_sent = False
        for admin_id in ADMIN_IDS:
            # Получаем язык администратора из базы данных
            admin_user = session.query(User).filter_by(telegram_id=admin_id, role='admin').first()
            admin_language = admin_user.language if admin_user and admin_user.language else 'en'

            notification_message = (
                f"💰 {get_text('vitrine_sold_product_title', admin_language)}\n"
                f"🏪 {get_text('vitrines', admin_language)}: {user.username}\n"
                f"📦 {get_text('product', admin_language)}: {product.name}\n"
                f"🔢 {get_text('quantity', admin_language)}: {quantity} {get_text('pcs', admin_language)}\n"
                f"📊 {get_text('balance', admin_language)} {get_text('on_vitrine', admin_language)}: {balance.quantity} {get_text('pcs', admin_language)}"
            )

            success = await safe_send_message(
                message.bot,
                admin_id,
                notification_message
            )
            if success:
                notification_sent = True

        if not notification_sent:
            log_error('sale_notification', 'Не удалось отправить уведомления администраторам', user.telegram_id)

        await VitrineStates.menu.set()

    except Exception as e:
        log_error('sale_creation', str(e), message.from_user.id)
        print(f"❌ Ошибка в enter_sale_quantity_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
        session.rollback()
    finally:
        session.close()


# 📊 ОТЧЕТЫ ВИТРИНЫ
async def vitrine_reports_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        balances = session.query(Balance).filter_by(vitrine_id=user.id).all()
        transactions = session.query(Transaction).filter(
            (Transaction.from_vitrine_id == user.id) |
            (Transaction.to_vitrine_id == user.id)
        ).all()

        report = format_report(user, balances, transactions, language=user.language)
        await message.answer(report)

    except Exception as e:
        print(f"❌ Ошибка в vitrine_reports_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


__all__ = [
    'vitrine_products_handler',
    'vitrine_returns_handler',
    'vitrine_sales_handler',
    'vitrine_reports_handler',
    'select_return_product_handler',
    'enter_return_quantity_handler',
    'select_sale_product_handler',
    'enter_sale_quantity_handler'
]