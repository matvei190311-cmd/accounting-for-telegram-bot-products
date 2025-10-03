from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import Database, User, Product, Transaction, Balance
from keyboards import (get_products_keyboard, get_vitrines_keyboard,
                       get_quantity_input_keyboard, get_main_keyboard,
                       get_operations_period_keyboard)
from states import AdminStates
from utils import get_text, format_report, split_message, safe_send_message
from confirmation_utils import send_confirmation_request
from export_utils import export_operations_to_csv
from datetime import datetime, timedelta
import io
from logger import log_operation, log_error

db = Database('sqlite:///bot.db')


def get_session():
    return db.get_session()


# 📦 ТОВАРЫ
async def admin_products_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        products = session.query(Product).all()

        await message.answer(
            get_text('products_list', user.language),
            reply_markup=get_products_keyboard(products, user.language)
        )

    except Exception as e:
        print(f"❌ Ошибка в admin_products_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


# 🏪 ВИТРИНЫ
async def admin_vitrines_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        vitrines = session.query(User).filter_by(role='vitrine').all()

        await message.answer(
            get_text('vitrines_list', user.language),
            reply_markup=get_vitrines_keyboard(vitrines, user.language)
        )
        await AdminStates.select_vitrine.set()

    except Exception as e:
        print(f"❌ Ошибка в admin_vitrines_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


# 1. 📦 ОТДАЧА ТОВАРА (требует подтверждения витриной)
async def select_vitrine_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        vitrine_name = message.text.replace("🏪 ", "")
        vitrine = session.query(User).filter_by(username=vitrine_name, role='vitrine').first()

        if vitrine:
            await state.update_data(selected_vitrine_id=vitrine.id)
            products = session.query(Product).all()

            await message.answer(
                get_text('select_product', user.language),
                reply_markup=get_products_keyboard(products, user.language)
            )
            await AdminStates.select_product.set()
        else:
            await message.answer(get_text('vitrine_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в select_vitrine_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def select_product_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        product_name = message.text.replace("📦 ", "")
        product = session.query(Product).filter_by(name=product_name).first()

        if product:
            await state.update_data(selected_product_id=product.id)
            await message.answer(
                get_text('enter_quantity', user.language),
                reply_markup=get_quantity_input_keyboard(user.language)
            )
            await AdminStates.enter_quantity.set()
        else:
            await message.answer(get_text('product_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в select_product_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def enter_quantity_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
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

        transaction = Transaction(
            type='give',
            product_id=data['selected_product_id'],
            quantity=quantity,
            to_vitrine_id=data['selected_vitrine_id'],
            admin_id=user.id,
            status='pending',
            needs_confirmation=True
        )
        session.add(transaction)
        session.commit()

        vitrine = session.query(User).get(data['selected_vitrine_id'])
        product = session.query(Product).get(data['selected_product_id'])

        confirmation_sent = await send_confirmation_request(transaction.id, message.bot)

        if confirmation_sent:
            await message.answer(
                get_text('give_request_sent', user.language),
                reply_markup=get_main_keyboard('admin', user.language)
            )
            log_operation(transaction.id, 'give_created',
                          f"Админ {user.username} отдает товар витрине {vitrine.username}")
        else:
            await message.answer(
                get_text('confirmation_error', user.language),
                reply_markup=get_main_keyboard('admin', user.language)
            )

        await AdminStates.menu.set()

    except Exception as e:
        print(f"❌ Ошибка в enter_quantity_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
        session.rollback()
    finally:
        session.close()


# 3. 📤 ЗАБОР ТОВАРА (не требует подтверждения)
async def admin_take_product_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        vitrines = session.query(User).filter_by(role='vitrine').all()

        await message.answer(
            get_text('select_vitrine_for_take', user.language),
            reply_markup=get_vitrines_keyboard(vitrines, user.language)
        )
        await AdminStates.take_select_vitrine.set()

    except Exception as e:
        print(f"❌ Ошибка в admin_take_product_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def take_select_vitrine_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        vitrine_name = message.text.replace("🏪 ", "")
        vitrine = session.query(User).filter_by(username=vitrine_name, role='vitrine').first()

        if vitrine:
            await state.update_data(take_vitrine_id=vitrine.id)
            balances = session.query(Balance).filter_by(vitrine_id=vitrine.id).filter(Balance.quantity > 0).all()
            products = [balance.product for balance in balances]

            if products:
                await message.answer(
                    f"📦 {get_text('products', user.language)} {get_text('vitrines', user.language)} {vitrine.username}:",
                    reply_markup=get_products_keyboard(products, user.language)
                )
                await AdminStates.take_select_product.set()
            else:
                await message.answer(get_text('no_products', user.language))
                await AdminStates.menu.set()
        else:
            await message.answer(get_text('vitrine_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в take_select_vitrine_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def take_select_product_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        product_name = message.text.replace("📦 ", "")
        product = session.query(Product).filter_by(name=product_name).first()

        if product:
            await state.update_data(take_product_id=product.id)
            await message.answer(
                get_text('enter_quantity', user.language),
                reply_markup=get_quantity_input_keyboard(user.language)
            )
            await AdminStates.take_enter_quantity.set()
        else:
            await message.answer(get_text('product_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в take_select_product_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def take_enter_quantity_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
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
            vitrine_id=data['take_vitrine_id'],
            product_id=data['take_product_id']
        ).first()

        if balance and balance.quantity >= quantity:
            transaction = Transaction(
                type='take',
                product_id=data['take_product_id'],
                quantity=quantity,
                from_vitrine_id=data['take_vitrine_id'],
                admin_id=user.id,
                status='confirmed'
            )
            session.add(transaction)
            balance.quantity -= quantity
            session.commit()

            vitrine = session.query(User).get(data['take_vitrine_id'])
            product = session.query(Product).get(data['take_product_id'])

            await message.answer(
                f"✅ {get_text('take_completed', user.language)}\n"
                f"🏪 {get_text('vitrines', user.language)}: {vitrine.username}\n"
                f"📦 {get_text('products', user.language)}: {product.name}\n"
                f"🔢 {get_text('quantity', user.language)}: {quantity} {get_text('pcs', user.language)}\n"
                f"📊 {get_text('new_balance', user.language)}: {balance.quantity} {get_text('pcs', user.language)}",
                reply_markup=get_main_keyboard('admin', user.language)
            )

            # ДИНАМИЧЕСКАЯ ЛОКАЛИЗАЦИЯ УВЕДОМЛЕНИЯ ДЛЯ ВИТРИНЫ
            vitrine_language = vitrine.language if vitrine.language else 'en'

            notification_message = (
                f"📤 {get_text('admin_took_product_title', vitrine_language)}\n"
                f"👤 {get_text('admin', vitrine_language)}: {user.username}\n"
                f"📦 {get_text('product', vitrine_language)}: {product.name}\n"
                f"🔢 {get_text('quantity', vitrine_language)}: {quantity} {get_text('pcs', vitrine_language)}\n"
                f"📊 {get_text('new_balance', vitrine_language)}: {balance.quantity} {get_text('pcs', vitrine_language)}"
            )

            # Безопасная отправка уведомления витрине
            await safe_send_message(
                message.bot,
                vitrine.telegram_id,
                notification_message
            )

            log_operation(transaction.id, 'take_completed',
                          f"Админ {user.username} забрал товар у витрины {vitrine.username}")

            await AdminStates.menu.set()
        else:
            await message.answer(get_text('not_enough_products', user.language))

    except Exception as e:
        print(f"❌ Ошибка в take_enter_quantity_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
        session.rollback()
    finally:
        session.close()


# 5. 🔄 ПЕРЕМЕЩЕНИЕ МЕЖДУ ВИТРИНАМИ (требует подтверждения получателем)
async def admin_transfer_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        vitrines = session.query(User).filter_by(role='vitrine').all()

        await message.answer(
            get_text('select_sender_vitrine', user.language),
            reply_markup=get_vitrines_keyboard(vitrines, user.language)
        )
        await AdminStates.transfer_select_from_vitrine.set()

    except Exception as e:
        print(f"❌ Ошибка в admin_transfer_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def transfer_select_from_vitrine_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        vitrine_name = message.text.replace("🏪 ", "")
        vitrine = session.query(User).filter_by(username=vitrine_name, role='vitrine').first()

        if vitrine:
            await state.update_data(transfer_from_vitrine_id=vitrine.id)
            balances = session.query(Balance).filter_by(vitrine_id=vitrine.id).filter(Balance.quantity > 0).all()
            products = [balance.product for balance in balances]

            if products:
                await message.answer(
                    f"📦 {get_text('products', user.language)} {get_text('vitrines', user.language)} {vitrine.username}:",
                    reply_markup=get_products_keyboard(products, user.language)
                )
                await AdminStates.transfer_select_product.set()
            else:
                await message.answer(get_text('no_products_for_transfer', user.language))
                await AdminStates.menu.set()
        else:
            await message.answer(get_text('vitrine_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в transfer_select_from_vitrine_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def transfer_select_product_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        product_name = message.text.replace("📦 ", "")
        product = session.query(Product).filter_by(name=product_name).first()

        if product:
            await state.update_data(transfer_product_id=product.id)
            data = await state.get_data()

            vitrines = session.query(User).filter_by(role='vitrine').filter(
                User.id != data['transfer_from_vitrine_id']).all()

            if vitrines:
                await message.answer(
                    get_text('select_receiver_vitrine', user.language),
                    reply_markup=get_vitrines_keyboard(vitrines, user.language)
                )
                await AdminStates.transfer_select_to_vitrine.set()
            else:
                await message.answer(get_text('no_other_vitrines', user.language))
                await AdminStates.menu.set()
        else:
            await message.answer(get_text('product_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в transfer_select_product_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def transfer_select_to_vitrine_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        vitrine_name = message.text.replace("🏪 ", "")
        vitrine = session.query(User).filter_by(username=vitrine_name, role='vitrine').first()

        if vitrine:
            await state.update_data(transfer_to_vitrine_id=vitrine.id)
            await message.answer(
                get_text('enter_transfer_quantity', user.language),
                reply_markup=get_quantity_input_keyboard(user.language)
            )
            await AdminStates.transfer_enter_quantity.set()
        else:
            await message.answer(get_text('vitrine_not_found', user.language))

    except Exception as e:
        print(f"❌ Ошибка в transfer_select_to_vitrine_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def transfer_enter_quantity_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
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

        from_balance = session.query(Balance).filter_by(
            vitrine_id=data['transfer_from_vitrine_id'],
            product_id=data['transfer_product_id']
        ).first()

        if from_balance and from_balance.quantity >= quantity:
            transaction = Transaction(
                type='transfer',
                product_id=data['transfer_product_id'],
                quantity=quantity,
                from_vitrine_id=data['transfer_from_vitrine_id'],
                to_vitrine_id=data['transfer_to_vitrine_id'],
                admin_id=user.id,
                status='pending',
                needs_confirmation=True
            )
            session.add(transaction)
            session.commit()

            from_vitrine = session.query(User).get(data['transfer_from_vitrine_id'])
            to_vitrine = session.query(User).get(data['transfer_to_vitrine_id'])
            product = session.query(Product).get(data['transfer_product_id'])

            confirmation_sent = await send_confirmation_request(transaction.id, message.bot)

            if confirmation_sent:
                await message.answer(
                    get_text('transfer_request_sent', user.language),
                    reply_markup=get_main_keyboard('admin', user.language)
                )
                log_operation(transaction.id, 'transfer_created',
                              f"Админ {user.username} перемещает товар от {from_vitrine.username} к {to_vitrine.username}")
            else:
                await message.answer(
                    get_text('confirmation_error', user.language),
                    reply_markup=get_main_keyboard('admin', user.language)
                )

            await AdminStates.menu.set()
        else:
            await message.answer(get_text('not_enough_products', user.language))

    except Exception as e:
        print(f"❌ Ошибка в transfer_enter_quantity_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
        session.rollback()
    finally:
        session.close()


# 📊 ОТЧЕТЫ
async def admin_reports_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        vitrines = session.query(User).filter_by(role='vitrine').all()

        for vitrine in vitrines:
            balances = session.query(Balance).filter_by(vitrine_id=vitrine.id).all()
            transactions = session.query(Transaction).filter(
                (Transaction.from_vitrine_id == vitrine.id) |
                (Transaction.to_vitrine_id == vitrine.id)
            ).all()

            report = format_report(vitrine, balances, transactions, language=user.language)
            await message.answer(report)

    except Exception as e:
        print(f"❌ Ошибка в admin_reports_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


# 📋 ЖУРНАЛ ОПЕРАЦИЙ
async def admin_operations_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        await message.answer(
            f"{get_text('operations_journal', user.language)}\n\n"
            f"{get_text('select_period', user.language)}:",
            reply_markup=get_operations_period_keyboard(user.language)
        )
        await AdminStates.operations_menu.set()

    except Exception as e:
        print(f"❌ Ошибка в admin_operations_handler: {e}")
        await message.answer(get_text('error_occurred', user.language))
    finally:
        session.close()


async def operations_menu_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        if get_text('back_to_main', user.language) in message.text:
            await message.answer(get_text('main_menu', user.language),
                                 reply_markup=get_main_keyboard('admin', user.language))
            await AdminStates.menu.set()
            return

        if message.text == get_text('all_operations', user.language):
            start_date = None
            end_date = None
            period_text = get_text('all_time', user.language)
        elif message.text == get_text('today', user.language):
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.now()
            period_text = get_text('today', user.language)
        elif message.text == get_text('week', user.language):
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()
            period_text = get_text('week', user.language)
        elif message.text == get_text('month', user.language):
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
            period_text = get_text('month', user.language)
        elif message.text == get_text('export_csv', user.language):
            await export_operations_csv(message, state)
            return
        else:
            await message.answer(get_text('select_period_from_list', user.language))
            return

        query = session.query(Transaction).order_by(Transaction.created_at.desc())
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)

        transactions = query.limit(100).all()

        if not transactions:
            await message.answer(
                f"📭 {get_text('operations_not_found', user.language)} {period_text}",
                reply_markup=get_main_keyboard('admin', user.language)
            )
            await AdminStates.menu.set()
            return

        report = f"{get_text('operations_journal', user.language)} ({period_text})\n\n"
        report += f"{get_text('total_operations', user.language)}: {len(transactions)}\n\n"

        for i, transaction in enumerate(transactions, 1):
            product = transaction.product
            emoji = get_transaction_emoji(transaction.type)
            type_text = get_transaction_type_text(transaction.type, user.language)

            report += f"{i}. {emoji} {type_text}\n"
            report += f"   📦 {get_text('products', user.language)}: {product.name} ({product.sku})\n"
            report += f"   🔢 {get_text('quantity', user.language)}: {transaction.quantity} шт.\n"

            if transaction.type == 'give' and transaction.to_vitrine:
                report += f"   🏪 {get_text('vitrines', user.language)}: {transaction.to_vitrine.username}\n"
            elif transaction.type in ['return', 'sale', 'take'] and transaction.from_vitrine:
                report += f"   🏪 {get_text('vitrines', user.language)}: {transaction.from_vitrine.username}\n"
            elif transaction.type == 'transfer':
                if transaction.from_vitrine:
                    report += f"   📤 {get_text('from', user.language)}: {transaction.from_vitrine.username}\n"
                if transaction.to_vitrine:
                    report += f"   📥 {get_text('to', user.language)}: {transaction.to_vitrine.username}\n"

            report += f"   ⏰ {get_text('date', user.language)}: {transaction.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            report += f"   ✅ {get_text('status', user.language)}: {transaction.status}\n"

            if i < len(transactions):
                report += "\n"

        if len(report) > 4000:
            parts = split_message(report)
            for part in parts:
                await message.answer(part)
        else:
            await message.answer(report)

        stats = get_operations_statistics(transactions)
        stats_report = f"{get_text('operations_statistics', user.language)} {period_text}:\n\n"
        stats_report += f"📦 {get_text('given', user.language)}: {stats['given']} шт.\n"
        stats_report += f"🔄 {get_text('returned', user.language)}: {stats['returned']} шт.\n"
        stats_report += f"💰 {get_text('sold', user.language)}: {stats['sold']} шт.\n"
        stats_report += f"📤 {get_text('taken', user.language)}: {stats['taken']} шт.\n"
        stats_report += f"🔄 {get_text('transferred', user.language)}: {stats['transferred']} шт.\n"

        await message.answer(stats_report)
        await message.answer(get_text('main_menu', user.language),
                             reply_markup=get_main_keyboard('admin', user.language))
        await AdminStates.menu.set()

    except Exception as e:
        print(f"❌ Ошибка в operations_menu_handler: {e}")
        user_lang = user.language if user else 'uz'
        await message.answer(get_text('error_occurred', user_lang))
    finally:
        session.close()

async def export_operations_csv(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        csv_data = export_operations_to_csv()

        if not csv_data:
            await message.answer(get_text('csv_export_error', user.language))
            return

        csv_file = io.BytesIO()
        csv_file.write(csv_data.encode('utf-8-sig'))
        csv_file.seek(0)

        await message.bot.send_document(
            chat_id=message.chat.id,
            document=types.InputFile(
                csv_file,
                filename=f"operations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            ),
            caption=get_text('export_csv', user.language)
        )

        await message.answer(get_text('main_menu', user.language),
                             reply_markup=get_main_keyboard('admin', user.language))
        await AdminStates.menu.set()

    except Exception as e:
        print(f"❌ Ошибка экспорта CSV: {e}")
        user_lang = user.language if user else 'uz'
        await message.answer(get_text('csv_export_error', user_lang))
    finally:
        session.close()

def get_transaction_emoji(transaction_type):
    emoji_map = {
        'give': '📤',
        'return': '🔄',
        'sale': '💰',
        'take': '📥',
        'transfer': '🔄'
    }
    return emoji_map.get(transaction_type, '📋')

def get_transaction_type_text(transaction_type, language='uz'):
    type_map = {
        'ru': {
            'give': 'Отдача товара',
            'return': 'Возврат товара',
            'sale': 'Продажа товара',
            'take': 'Забор товара',
            'transfer': 'Перемещение товара'
        },
        'uz': {
            'give': 'Mahsulot berish',
            'return': 'Mahsulot qaytarish',
            'sale': 'Mahsulot sotish',
            'take': 'Mahsulot olish',
            'transfer': 'Mahsulot ko\'chirish'
        },
        'en': {
            'give': 'Product Give',
            'return': 'Product Return',
            'sale': 'Product Sale',
            'take': 'Product Take',
            'transfer': 'Product Transfer'
        }
    }
    texts = type_map.get(language, type_map['en'])
    return texts.get(transaction_type, 'Unknown operation')

def get_operations_statistics(transactions):
    stats = {
        'given': 0,
        'returned': 0,
        'sold': 0,
        'taken': 0,
        'transferred': 0
    }

    for transaction in transactions:
        if transaction.type == 'give':
            stats['given'] += transaction.quantity
        elif transaction.type == 'return':
            stats['returned'] += transaction.quantity
        elif transaction.type == 'sale':
            stats['sold'] += transaction.quantity
        elif transaction.type == 'take':
            stats['taken'] += transaction.quantity
        elif transaction.type == 'transfer':
            stats['transferred'] += transaction.quantity

    return stats


__all__ = [
    'admin_products_handler',
    'admin_vitrines_handler',
    'admin_reports_handler',
    'admin_operations_handler',
    'admin_take_product_handler',
    'admin_transfer_handler',
    'select_vitrine_handler',
    'select_product_handler',
    'enter_quantity_handler',
    'take_select_vitrine_handler',
    'take_select_product_handler',
    'take_enter_quantity_handler',
    'transfer_select_from_vitrine_handler',
    'transfer_select_product_handler',
    'transfer_select_to_vitrine_handler',
    'transfer_enter_quantity_handler',
    'operations_menu_handler'
]