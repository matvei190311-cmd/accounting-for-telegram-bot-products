from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import Database, User
from keyboards import get_main_keyboard, generate_confirmation_patterns, generate_menu_patterns
from utils import get_text, get_language_keyboard, get_available_languages
from states import AdminStates, VitrineStates, AuthStates
from config import ADMIN_IDS, VITRINE_PASSWORD
from confirmation_utils import process_confirmation_reply
from .handlers_imports import get_admin_handler, get_vitrine_handler, get_admin_state_handler

db = Database('sqlite:///bot.db')


def get_session():
    return db.get_session()


async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if user:
            await message.answer(
                get_text('welcome_back', user.language, role=user.role),
                reply_markup=get_main_keyboard(user.role, user.language)
            )
            if user.role == 'admin':
                await AdminStates.menu.set()
            else:
                await VitrineStates.menu.set()
        else:
            # ДИНАМИЧЕСКИЙ ВЫБОР ЯЗЫКА ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ (включая админов)
            await message.answer(
                get_text('welcome_choose_language', 'en'),
                reply_markup=get_language_keyboard()
            )
            await state.update_data(new_user_id=user_id)

            # Устанавливаем состояние выбора языка для всех новых пользователей
            if user_id in ADMIN_IDS:
                await AdminStates.language_selection.set()
            else:
                await VitrineStates.language_selection.set()

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))
    finally:
        session.close()


async def language_selection_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        data = await state.get_data()
        user_id = data.get('new_user_id', message.from_user.id)

        # Динамически определяем выбранный язык
        language_map = {
            '🇷🇺 Русский': 'ru',
            "🇺🇿 O'zbek": 'uz',
            '🇺🇸 English': 'en',
            '🇩🇪 Deutsch': 'de',
            '🇫🇷 Français': 'fr',
            '🇪🇸 Español': 'es',
            '🇨🇳 中文': 'zh',
            '🇸🇦 العربية': 'ar',
            '🇹🇷 Türkçe': 'tr',
            '🇰🇷 한국어': 'ko',
            '🇯🇵 日本語': 'ja'
        }

        selected_language = language_map.get(message.text)

        if not selected_language:
            # Пробуем найти язык по доступным кодам
            available_langs = get_available_languages()
            for lang_code in available_langs:
                if message.text.endswith(lang_code.upper()):
                    selected_language = lang_code
                    break

        if not selected_language:
            await message.answer(get_text('choose_language_from_list', 'en'))
            return

        # Проверяем, что выбранный язык доступен
        if selected_language not in get_available_languages():
            await message.answer(get_text('language_not_available', 'en'))
            return

        role = 'admin' if user_id in ADMIN_IDS else 'vitrine'

        # Проверяем, существует ли уже пользователь
        existing_user = session.query(User).filter_by(telegram_id=user_id).first()

        if existing_user:
            # Обновляем язык существующего пользователя
            existing_user.language = selected_language
            session.commit()

            await message.answer(
                get_text('language_changed', selected_language),
                reply_markup=get_main_keyboard(role, selected_language)
            )

            if role == 'admin':
                await AdminStates.menu.set()
            else:
                await VitrineStates.menu.set()

        else:
            # Создаем нового пользователя
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                role=role,
                language=selected_language
            )
            session.add(user)
            session.commit()

            if role == 'admin':
                await message.answer(
                    get_text('welcome_admin', selected_language),
                    reply_markup=get_main_keyboard('admin', selected_language)
                )
                await AdminStates.menu.set()
            else:
                await message.answer(
                    get_text('enter_password', selected_language),
                    reply_markup=types.ReplyKeyboardRemove()
                )
                await AuthStates.waiting_password.set()
                await state.update_data(user_language=selected_language)

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))
        session.rollback()
    finally:
        session.close()


async def password_handler(message: types.Message, state: FSMContext):
    session = get_session()
    try:
        data = await state.get_data()
        language = data.get('user_language', 'en')

        if message.text == VITRINE_PASSWORD:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if user:
                user.role = 'vitrine'
                session.commit()

                await message.answer(
                    get_text('welcome_vitrine', language),
                    reply_markup=get_main_keyboard('vitrine', language)
                )
                await VitrineStates.menu.set()
        else:
            await message.answer(get_text('wrong_password', language))

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))
        session.rollback()
    finally:
        session.close()


async def back_to_main_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if user:
            await message.answer(
                get_text('main_menu', user.language),
                reply_markup=get_main_keyboard(user.role, user.language)
            )
            if user.role == 'admin':
                await AdminStates.menu.set()
            else:
                await VitrineStates.menu.set()
        else:
            await start_handler(message, state)

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))
    finally:
        session.close()


async def main_menu_handler(message: types.Message, state: FSMContext):
    await back_to_main_handler(message, state)


async def confirmation_reply_handler(message: types.Message, state: FSMContext):
    """Обработчик reply-кнопок подтверждения - полностью динамический"""
    try:
        text = message.text

        # Динамически определяем, является ли это кнопкой подтверждения/отклонения
        confirmation_patterns = generate_confirmation_patterns()

        is_confirmation = False
        is_confirm = False
        transaction_id = None

        for pattern in confirmation_patterns:
            if pattern in text:
                is_confirmation = True
                # Определяем тип кнопки (подтверждение или отклонение)
                if "✅" in pattern:
                    is_confirm = True
                else:
                    is_confirm = False
                # Извлекаем ID транзакции
                try:
                    transaction_id = int(text.split("_")[1])
                except (IndexError, ValueError):
                    print(f"❌ Не удалось извлечь ID транзакции из текста: {text}")
                    return False
                break

        if not is_confirmation or transaction_id is None:
            return False

        success = await process_confirmation_reply(message, is_confirm, transaction_id)

        if success:
            user_id = message.from_user.id
            session = get_session()
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                await message.answer(
                    get_text('main_menu', user.language),
                    reply_markup=get_main_keyboard(user.role, user.language)
                )
                if user.role == 'admin':
                    await AdminStates.menu.set()
                else:
                    await VitrineStates.menu.set()
            session.close()
            return True
        return False

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))
        return False


async def dynamic_menu_handler(message: types.Message, state: FSMContext):
    """Динамический обработчик для всех кнопок меню"""
    try:
        user_id = message.from_user.id
        session = get_session()
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if not user:
            await start_handler(message, state)
            return

        text = message.text
        user_language = user.language

        # Получаем все возможные тексты кнопок для текущего языка пользователя
        menu_texts = {
            'products': get_text('products', user_language),
            'vitrines': get_text('vitrines', user_language),
            'reports': get_text('reports', user_language),
            'operations': get_text('operations', user_language),
            'take_product': get_text('take_product', user_language),
            'transfer': get_text('transfer', user_language),
            'returns': get_text('returns', user_language),
            'sales': get_text('sales', user_language),
            'change_language': get_text('change_language', user_language)
        }

        # Определяем, какая кнопка была нажата
        handler_key = None

        if text == menu_texts['products']:
            handler_key = 'products'
        elif text == menu_texts['vitrines'] and user.role == 'admin':
            handler_key = 'vitrines'
        elif text == menu_texts['reports']:
            handler_key = 'reports'
        elif text == menu_texts['operations'] and user.role == 'admin':
            handler_key = 'operations'
        elif text == menu_texts['take_product'] and user.role == 'admin':
            handler_key = 'take_product'
        elif text == menu_texts['transfer'] and user.role == 'admin':
            handler_key = 'transfer'
        elif text == menu_texts['returns'] and user.role == 'vitrine':
            handler_key = 'returns'
        elif text == menu_texts['sales'] and user.role == 'vitrine':
            handler_key = 'sales'
        elif text == menu_texts['change_language']:
            await change_language_handler(message, state)
            session.close()
            return

        if handler_key:
            # Получаем соответствующий обработчик
            if user.role == 'admin':
                handler = get_admin_handler(handler_key)
            else:
                handler = get_vitrine_handler(handler_key)

            if handler:
                await handler(message, state)
            else:
                await back_to_main_handler(message, state)
        else:
            # Если кнопка не распознана, возвращаем в главное меню
            await back_to_main_handler(message, state)

        session.close()

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))


async def dynamic_state_handler(message: types.Message, state: FSMContext):
    """Динамический обработчик для состояний (выбор витрин, товаров и т.д.)"""
    try:
        user_id = message.from_user.id
        session = get_session()
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if not user:
            await start_handler(message, state)
            return

        current_state = await state.get_state()
        user_language = user.language

        # Определяем обработчик на основе текущего состояния
        handler = None

        if current_state == AdminStates.select_vitrine.state:
            handler = get_admin_state_handler('select_vitrine')
        elif current_state == AdminStates.select_product.state:
            handler = get_admin_state_handler('select_product')
        elif current_state == AdminStates.enter_quantity.state:
            handler = get_admin_state_handler('enter_quantity')
        elif current_state == AdminStates.take_select_vitrine.state:
            handler = get_admin_state_handler('take_select_vitrine')
        elif current_state == AdminStates.take_select_product.state:
            handler = get_admin_state_handler('take_select_product')
        elif current_state == AdminStates.take_enter_quantity.state:
            handler = get_admin_state_handler('take_enter_quantity')
        elif current_state == AdminStates.transfer_select_from_vitrine.state:
            handler = get_admin_state_handler('transfer_select_from_vitrine')
        elif current_state == AdminStates.transfer_select_product.state:
            handler = get_admin_state_handler('transfer_select_product')
        elif current_state == AdminStates.transfer_select_to_vitrine.state:
            handler = get_admin_state_handler('transfer_select_to_vitrine')
        elif current_state == AdminStates.transfer_enter_quantity.state:
            handler = get_admin_state_handler('transfer_enter_quantity')
        elif current_state == AdminStates.operations_menu.state:
            handler = get_admin_state_handler('operations_menu')
        elif current_state == VitrineStates.select_return_product.state:
            from .vitrine import select_return_product_handler
            handler = select_return_product_handler
        elif current_state == VitrineStates.enter_return_quantity.state:
            from .vitrine import enter_return_quantity_handler
            handler = enter_return_quantity_handler
        elif current_state == VitrineStates.select_sale_product.state:
            from .vitrine import select_sale_product_handler
            handler = select_sale_product_handler
        elif current_state == VitrineStates.enter_sale_quantity.state:
            from .vitrine import enter_sale_quantity_handler
            handler = enter_sale_quantity_handler

        if handler:
            await handler(message, state)
        else:
            # Если состояние не распознано, возвращаем в главное меню
            await back_to_main_handler(message, state)

        session.close()

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))


async def change_language_handler(message: types.Message, state: FSMContext):
    """Обработчик смены языка из главного меню"""
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

        if not user:
            await start_handler(message, state)
            return

        # Показываем клавиатуру выбора языка
        await message.answer(
            get_text('choose_language', user.language),
            reply_markup=get_language_keyboard()
        )

        # Сохраняем текущую роль для возврата
        await state.update_data(
            current_role=user.role,
            changing_language=True
        )

        if user.role == 'admin':
            await AdminStates.language_selection.set()
        else:
            await VitrineStates.language_selection.set()

    except Exception as e:
        print(f"❌ {get_text('error_in_handler', 'en')}: {e}")
        await message.answer(get_text('error_occurred', 'en'))
    finally:
        session.close()


def register_common_handlers(dp: Dispatcher):
    # Получаем доступные языки для фильтрации
    available_langs = get_available_languages()
    language_buttons = []

    for lang_code in available_langs:
        if lang_code == 'ru':
            language_buttons.append("🇷🇺 Русский")
        elif lang_code == 'uz':
            language_buttons.append("🇺🇿 O'zbek")
        elif lang_code == 'en':
            language_buttons.append("🇺🇸 English")
        elif lang_code == 'de':
            language_buttons.append("🇩🇪 Deutsch")
        elif lang_code == 'fr':
            language_buttons.append("🇫🇷 Français")
        elif lang_code == 'es':
            language_buttons.append("🇪🇸 Español")
        elif lang_code == 'zh':
            language_buttons.append("🇨🇳 中文")
        elif lang_code == 'ar':
            language_buttons.append("🇸🇦 العربية")
        elif lang_code == 'tr':
            language_buttons.append("🇹🇷 Türkçe")
        elif lang_code == 'ko':
            language_buttons.append("🇰🇷 한국어")
        elif lang_code == 'ja':
            language_buttons.append("🇯🇵 日本語")
        else:
            language_buttons.append(f"🌐 {lang_code.upper()}")

    dp.register_message_handler(start_handler, commands=['start'], state='*')
    dp.register_message_handler(language_selection_handler,
                                lambda m: m.text in language_buttons,
                                state=[AdminStates.language_selection, VitrineStates.language_selection,
                                       AuthStates.waiting_password, AdminStates.menu, VitrineStates.menu])
    dp.register_message_handler(password_handler, state=AuthStates.waiting_password)


    # Динамически обрабатываем кнопки "Назад" для всех языков
    back_phrases = []
    for lang_code in available_langs:
        back_text = get_text('back_to_main', lang_code)
        if back_text and back_text not in back_phrases:
            back_phrases.append(back_text)

    dp.register_message_handler(main_menu_handler,
                                lambda m: any(phrase in m.text for phrase in back_phrases),
                                state='*')

    # Обработчик reply-кнопок подтверждения - динамически генерируем паттерны
    confirmation_patterns = generate_confirmation_patterns()

    dp.register_message_handler(confirmation_reply_handler,
                                lambda m: any(pattern in m.text for pattern in confirmation_patterns),
                                state='*')

    # Динамический обработчик для всех кнопок меню
    menu_patterns = generate_menu_patterns()

    dp.register_message_handler(dynamic_menu_handler,
                                lambda m: any(pattern in m.text for pattern in menu_patterns),
                                state=[AdminStates.menu, VitrineStates.menu])
    
    # Динамический обработчик для всех состояний (кроме меню и подтверждений)
    dp.register_message_handler(dynamic_state_handler, state='*')


__all__ = ['register_common_handlers']