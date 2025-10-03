import logging
import os
from datetime import datetime
from database import Database

# Создаем папку для логов если её нет
if not os.path.exists('logs'):
    os.makedirs('logs')

# Настраиваем логгер для операций
operations_logger = logging.getLogger('operations')
operations_logger.setLevel(logging.INFO)

# Форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Файловый обработчик для операций
file_handler = logging.FileHandler(f'logs/operations_{datetime.now().strftime("%Y%m")}.log', encoding='utf-8')
file_handler.setFormatter(formatter)
operations_logger.addHandler(file_handler)

# Логгер для ошибок
error_logger = logging.getLogger('errors')
error_logger.setLevel(logging.ERROR)
error_file_handler = logging.FileHandler(f'logs/errors_{datetime.now().strftime("%Y%m")}.log', encoding='utf-8')
error_file_handler.setFormatter(formatter)
error_logger.addHandler(error_file_handler)

db = Database('sqlite:///bot.db')


def log_operation(transaction_id, operation_type, details):
    """Логирует операцию в файл и выводит в консоль"""
    session = db.get_session()
    try:
        transaction = session.query(Transaction).get(transaction_id)
        if not transaction:
            operations_logger.error(f"Транзакция не найдена: {transaction_id}")
            return

        # Формируем детали операции
        product_name = transaction.product.name if transaction.product else "Неизвестный товар"

        log_message = f"OPERATION: {operation_type.upper()} | "
        log_message += f"ID: {transaction_id} | "
        log_message += f"Product: {product_name} | "
        log_message += f"Quantity: {transaction.quantity} | "
        log_message += f"Status: {transaction.status} | "

        # Добавляем информацию об участниках в зависимости от типа операции
        if operation_type == 'give' and transaction.to_vitrine:
            log_message += f"To: {transaction.to_vitrine.username} | "
        elif operation_type in ['return', 'sale', 'take'] and transaction.from_vitrine:
            log_message += f"From: {transaction.from_vitrine.username} | "
        elif operation_type == 'transfer':
            if transaction.from_vitrine:
                log_message += f"From: {transaction.from_vitrine.username} | "
            if transaction.to_vitrine:
                log_message += f"To: {transaction.to_vitrine.username} | "

        if transaction.admin:
            log_message += f"Admin: {transaction.admin.username} | "

        log_message += f"Details: {details}"

        # Записываем в лог
        operations_logger.info(log_message)
        print(f"📝 LOGGED: {log_message}")

    except Exception as e:
        error_logger.error(f"Ошибка логирования операции {transaction_id}: {e}")
        print(f"❌ Ошибка логирования: {e}")
    finally:
        session.close()


def log_error(operation_type, error_message, user_id=None):
    """Логирует ошибки в отдельный файл"""
    error_msg = f"ERROR: {operation_type} | User: {user_id} | Message: {error_message}"
    error_logger.error(error_msg)
    print(f"❌ ERROR LOGGED: {error_msg}")


def get_operations_log(limit=100):
    """Возвращает последние операции из лог-файла"""
    try:
        log_file = f'logs/operations_{datetime.now().strftime("%Y%m")}.log'
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return lines[-limit:] if len(lines) > limit else lines
        return []
    except Exception as e:
        error_logger.error(f"Ошибка чтения лог-файла: {e}")
        return []


# Импортируем здесь чтобы избежать циклического импорта
from database import Transaction