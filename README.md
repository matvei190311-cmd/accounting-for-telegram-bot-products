# # 🤖 Telegram Bot для управления товарами и витринами

Многоязычный Telegram бот для управления товарами, витринами и операциями с товарами. Поддерживает роли администратора и витрины с различными типами операций.

Multi-language Telegram bot for managing products, showcases, and product operations. Supports administrator and showcase roles with various operation types.

## 🌍 Поддерживаемые языки / Supported Languages

- 🇷🇺 **Русский** (Russian)
- 🇺🇿 **O'zbek** (Uzbek) 
- 🇺🇸 **English** (English)
- 🇩🇪 **Deutsch** (German)
- 🇫🇷 **Français** (French)
- 🇪🇸 **Español** (Spanish)

*Система поддерживает динамическое добавление новых языков без изменения кода!*

## 🚀 Основные возможности / Key Features

### 👨‍💼 Для администраторов / For Administrators:
- **📦 Отдача товара витринам** (требует подтверждения) / **Product give to showcases** (requires confirmation)
- **📤 Забор товара с витрин** (без подтверждения) / **Product take from showcases** (no confirmation required)
- **🔄 Перемещение товара между витринами** (требует подтверждения) / **Product transfer between showcases** (requires confirmation)
- **📊 Просмотр отчетов** по витринам / **View reports** for showcases
- **📋 Журнал операций** с фильтрацией по периодам / **Operations journal** with period filtering
- **📁 Экспорт операций** в CSV / **Export operations** to CSV
- **👥 Управление витринами** / **Showcase management**

### 🏪 Для витрин / For Showcases:
- **📦 Просмотр доступных товаров** / **View available products**
- **🔄 Возврат товара администратору** (требует подтверждения) / **Product return to administrator** (requires confirmation)
- **💰 Продажа товара** (без подтверждения) / **Product sale** (no confirmation required)
- **📊 Отчеты** по операциям / **Reports** on operations

## 🛠 Технологии / Technologies

- **Python 3.8+**
- **Aiogram** (асинхронный Telegram Bot API) / (asynchronous Telegram Bot API)
- **SQLAlchemy** (ORM для работы с базой данных) / (ORM for database operations)
- **SQLite** (база данных по умолчанию) / (default database)
- **Динамическая локализация** (поддержка 6+ языков) / **Dynamic localization** (6+ languages support)

## 📦 Установка и настройка / Installation and Setup

### 1. Клонирование репозитория / Clone repository
```bash
git clone https://github.com/matvei190311-cmd/accounting-for-telegram-bot-products
cd <project-folder>
```

### 2. Установка зависимостей / Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Настройка окружения / Environment setup
Создайте файл `.env` в корне проекта / Create `.env` file in project root:
```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321
VITRINE_PASSWORD=your_vitrine_password
DEFAULT_LANGUAGE=uz
DATABASE_URL=sqlite:///bot.db
```

### 4. Запуск бота / Start bot
```bash
python main.py
```

## 🗃 Структура проекта / Project Structure

```
├── handlers/
│   ├── __init__.py          # Регистрация всех обработчиков
│   ├── common.py            # Общие обработчики (старт, язык)
│   ├── admin.py             # Обработчики для администраторов
│   ├── vitrine.py           # Обработчики для витрин
│   └── handlers_imports.py  # Динамические импорты
├── locales/                 # Файлы локализации
│   ├── ru.json             # Русский
│   ├── uz.json             # Узбекский
│   ├── en.json             # Английский
│   ├── de.json             # Немецкий
│   ├── fr.json             # Французский
│   └── es.json             # Испанский
├── database.py              # Модели и работа с БД
├── keyboards.py             # Динамические клавиатуры
├── states.py                # Состояния FSM
├── utils.py                 # Вспомогательные функции
├── config.py                # Конфигурация
├── confirmation_utils.py    # Утилиты подтверждения операций
├── export_utils.py          # Экспорт в CSV
├── logger.py                # Логирование операций
└── main.py                  # Точка входа
```

## 🔐 Роли и доступы / Roles and Access

### Администратор / Administrator
- Доступ ко всем функциям управления / Access to all management functions
- Просмотр всех витрин и операций / View all showcases and operations
- Подтверждение операций возврата / Confirm return operations
- Экспорт данных в CSV / Export data to CSV

### Витрина / Showcase
- Управление только своими товарами / Manage only own products
- Продажа и возврат товаров / Sell and return products
- Просмотр своих отчетов / View own reports

## 📊 Типы операций / Operation Types

1. **📤 Give (Отдача)** - администратор → витрина (требует подтверждения) / administrator → showcase (requires confirmation)
2. **🔄 Return (Возврат)** - витрина → администратор (требует подтверждения) / showcase → administrator (requires confirmation)
3. **💰 Sale (Продажа)** - витрина → клиент (без подтверждения) / showcase → client (no confirmation required)
4. **📥 Take (Забор)** - администратор ← витрина (без подтверждения) / administrator ← showcase (no confirmation required)
5. **🔄 Transfer (Перемещение)** - витрина → витрина (требует подтверждения) / showcase → showcase (requires confirmation)

## 🌍 Динамическая локализация / Dynamic Localization

### Добавление нового языка / Adding new language:
1. Создайте файл `locales/код_языка.json` / Create `locales/language_code.json`
2. Добавьте переводы всех ключей / Add translations for all keys
3. Перезапустите бота / Restart bot

**Пример / Example:**
```json
{
  "welcome_admin": "Welcome! You have logged in as administrator.",
  "products": "📦 Products",
  "confirm": "Confirm",
  "reject": "Reject"
}
```

### Автоматические функции / Automatic features:
- ✅ Автоопределение доступных языков / Auto-detection of available languages
- ✅ Динамические клавиатуры / Dynamic keyboards
- ✅ Локализованные уведомления / Localized notifications
- ✅ Поддержка кнопок подтверждения / Confirmation buttons support

## 🗃 База данных / Database

### Основные таблицы / Main tables:
- **users** - пользователи (администраторы и витрины) / users (administrators and showcases)
- **products** - товары с SKU / products with SKU
- **transactions** - транзакции операций / transaction operations
- **balances** - остатки товаров на витринах / product balances on showcases

## 📝 Логирование / Logging

- Операции логируются в файлы `logs/operations_YYYYMM.log` / Operations logged to `logs/operations_YYYYMM.log`
- Ошибки сохраняются в `logs/errors_YYYYMM.log` / Errors saved to `logs/errors_YYYYMM.log`
- Детальная информация о каждой операции / Detailed information about each operation

## 🔧 Конфигурация / Configuration

Основные настройки в `config.py` / Main settings in `config.py`:
- `BOT_TOKEN` - токен бота от @BotFather / bot token from @BotFather
- `ADMIN_IDS` - список ID администраторов через запятую / list of administrator IDs separated by commas
- `VITRINE_PASSWORD` - пароль для регистрации витрин / password for showcase registration
- `DEFAULT_LANGUAGE` - язык по умолчанию / default language

## 📈 Отчеты / Reports

Система формирует детальные отчеты по / System generates detailed reports for:
- Остаткам товаров / Product balances
- Движениям за период / Movements for the period
- Статистике операций / Operation statistics
- Продажам и возвратам / Sales and returns

## 🚨 Безопасность / Security

- Подтверждение критических операций / Confirmation of critical operations
- Валидация вводимых данных / Input data validation
- Безопасная отправка сообщений / Secure message sending
- Логирование всех действий / Logging of all actions

## 💡 Особенности системы / System Features

### 🎯 Динамическая архитектура / Dynamic Architecture
- Добавление языков без изменения кода / Add languages without code changes
- Автоматическое обнаружение новых локалей / Automatic detection of new locales
- Гибкая система обработчиков / Flexible handler system

### 🔄 Умные уведомления / Smart Notifications
- Локализованные сообщения для каждого пользователя / Localized messages for each user
- Автоматический выбор языка получателя / Automatic recipient language selection
- Поддержка всех типов операций / Support for all operation types

### 📊 Полная отчетность / Complete Reporting
- Детальная статистика операций / Detailed operation statistics
- Фильтрация по периодам / Period filtering
- Экспорт в CSV для анализа / CSV export for analysis

## 🐛 Отладка / Debugging

При проблемах проверьте / If issues occur, check:
1. Файлы логов в папке `logs/` / Log files in `logs/` folder
2. Корректность токена бота / Bot token correctness
3. Наличие всех файлов локализации / Presence of all localization files
4. Доступ к базе данных / Database access

## 📄 Лицензия / License

[Указать лицензию] / [Specify license]

---

**Разработано для управления товарными потоками между администраторами и витринами**  
**Developed for managing product flows between administrators and showcases**
