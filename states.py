from aiogram.dispatcher.filters.state import State, StatesGroup


class AdminStates(StatesGroup):
    menu = State()
    language_selection = State()

    # Отдача товара
    select_vitrine = State()
    select_product = State()
    enter_quantity = State()

    # Забор товара
    take_select_vitrine = State()
    take_select_product = State()
    take_enter_quantity = State()

    # Перемещение товара
    transfer_select_from_vitrine = State()
    transfer_select_product = State()
    transfer_select_to_vitrine = State()
    transfer_enter_quantity = State()

    # Операции (журнал)
    operations_menu = State()

    reports = State()


class VitrineStates(StatesGroup):
    menu = State()
    language_selection = State()

    # Возврат товара
    select_return_product = State()
    enter_return_quantity = State()

    # Продажа товара
    select_sale_product = State()
    enter_sale_quantity = State()


class AuthStates(StatesGroup):
    waiting_password = State()