# ValutaTrade Hub

Консольное приложение для управления виртуальным портфелем фиатных и криптовалют.

## Описание проекта

ValutaTrade Hub — это комплексная платформа, которая позволяет пользователям:

- Регистрироваться и управлять аккаунтами
- Управлять виртуальным портфелем фиатных и криптовалют
- Совершать сделки по покупке/продаже валют
- Отслеживать актуальные курсы валют в реальном времени

Система состоит из двух основных сервисов:

- **Parser Service**: Отдельное приложение, которое обращается к публичным API (CoinGecko, ExchangeRate-API), получает актуальные курсы и сохраняет историю в базу данных.
- **Core Service**: Главное приложение, которое предоставляет CLI интерфейс, управляет пользователями, их кошельками и взаимодействует с Parser Service для получения актуальных курсов.

## Структура проекта

```
finalproject_kalenskiy_M25-555/
│
├── data/
│   ├── users.json              # Пользователи системы
│   ├── portfolios.json         # Портфели и кошельки
│   ├── rates.json              # Кеш курсов для Core Service
│   └── exchange_rates.json     # Исторический журнал курсов
│
├── valutatrade_hub/
│   ├── __init__.py
│   ├── logging_config.py       # Настройка логирования
│   ├── decorators.py           # Декораторы (@log_action и др.)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── currencies.py       # Иерархия валют (Currency, FiatCurrency, CryptoCurrency)
│   │   ├── exceptions.py       # Пользовательские исключения
│   │   ├── models.py           # Основные модели (User, Wallet, Portfolio)
│   │   ├── usecases.py         # Бизнес-логика (UserManager, PortfolioManager, RateManager)
│   │   └── utils.py            # Вспомогательные функции
│   │
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── settings.py         # Singleton SettingsLoader (конфигурация)
│   │   └── database.py         # Singleton DatabaseManager (абстракция над JSON)
│   │
│   ├── parser_service/
│   │   ├── __init__.py
│   │   ├── config.py           # Конфигурация API и параметров обновления
│   │   ├── api_clients.py      # Клиенты для CoinGecko и ExchangeRate-API
│   │   ├── updater.py          # Основной модуль обновления курсов
│   │   └── storage.py          # Операции чтения/записи файлов курсов
│   │
│   └── cli/
│       ├── __init__.py
│       └── interface.py        # CLI команды
│
├── main.py                     # Точка входа в приложение
├── Makefile                    # Автоматизация команд
├── pyproject.toml              # Конфигурация Poetry
├── README.md                   # Документация
└── .gitignore                  # Игнорируемые файлы
```

## Установка

### Предварительные требования

- Python 3.11+
- Poetry

### Шаги установки

1. Клонируйте репозиторий:
```bash
git clone <repository_url>
cd finalproject_kalenskiy_M25-555
```

2. Установите зависимости:
```bash
make install
```

Или напрямую через Poetry:
```bash
poetry install
```

## Запуск приложения

### Основной способ

```bash
make project
```

Или через Poetry:
```bash
poetry run project
```

### Доступные команды

#### Регистрация и авторизация

```bash
# Регистрация нового пользователя
poetry run project register --username alice --password 1234

# Вход в систему
poetry run project login --username alice --password 1234
```

#### Управление портфелем

```bash
# Показать портфель
poetry run project show-portfolio
poetry run project show-portfolio --base EUR

# Купить валюту
poetry run project buy --currency BTC --amount 0.05

# Продать валюту
poetry run project sell --currency BTC --amount 0.01

# Получить курс валюты
poetry run project get-rate --from USD --to BTC
```

## Демонстрация работы приложения
показан полный цикл: register → login → buy/sell → show-portfolio → get-rate; отдельно — update-rates и show-rates, демонстрация обработки ошибок (например, недостаточно средств/неизвестная валюта).
[![asciicast](https://asciinema.org/a/kpckt3hLzGvqNZiMz4AayunSH.svg)](https://asciinema.org/a/kpckt3hLzGvqNZiMz4AayunSH)

#### Обновление курсов (Parser Service)

```bash
# Обновить все курсы
poetry run project update-rates

# Обновить только криптовалюты
poetry run project update-rates --source coingecko

# Обновить только фиатные валюты
poetry run project update-rates --source exchangerate

# Показать курсы из кеша
poetry run project show-rates

# Показать топ-3 криптовалюты
poetry run project show-rates --top 3

# Показать курс конкретной валюты
poetry run project show-rates --currency BTC
```

## Настройка Parser Service

### Получение и установка API ключей

#### ExchangeRate-API (для фиатных валют)

1. Зарегистрируйтесь на https://www.exchangerate-api.com/
2. После регистрации вы получите API ключ
3. Установите ключ в переменную окружения:
```bash
export EXCHANGERATE_API_KEY="ваш_ключ"
```

Для постоянного использования добавьте в `~/.zshrc` или `~/.bashrc`:
```bash
echo 'export EXCHANGERATE_API_KEY="ваш_ключ"' >> ~/.zshrc
source ~/.zshrc
```

#### CoinGecko (для криптовалют)

- **Бесплатный доступ**: Работает без ключа, но с ограничениями по частоте запросов
- **Платный доступ** (опционально): Зарегистрируйтесь на https://www.coingecko.com/en/api для получения ключа

**Примечание**: Без ExchangeRate-API ключа можно работать только с криптовалютами.

### Кэш курсов и TTL

Приложение использует кэширование курсов валют для повышения производительности:

- **Файл кеша**: `data/rates.json` — содержит последние обновлённые курсы
- **Исторический журнал**: `data/exchange_rates.json` — хранит все исторические записи курсов
- **TTL (Time To Live)**: По умолчанию курсы считаются свежими 5 минут (300 секунд)

Если курс в кеше устарел, приложение предложит обновить данные через команду `update-rates`.

Настройка TTL:
- Значение задаётся в `valutatrade_hub/infra/settings.py` в параметре `rates_ttl_seconds`
- По умолчанию: 300 секунд (5 минут)

### Расписание обновления

Для автоматического обновления курсов можно использовать системный планировщик:

**Linux/macOS (cron):**
```bash
# Обновлять каждые 5 минут
*/5 * * * * cd /path/to/project && poetry run project update-rates
```

**Или через Python скрипт:**
Используйте модуль `scheduler.py` (если реализован) для периодического запуска обновления.

## Разработка

### Проверка кода

```bash
make lint
```

Или напрямую:
```bash
poetry run ruff check .
```

### Сборка пакета

```bash
make build
```

### Установка собранного пакета

```bash
make package-install
```

### Проверка публикации

```bash
make publish
```

## Логирование

Логи приложения сохраняются в файл `logs/actions.log`:

- **Уровень логирования**: INFO (по умолчанию)
- **Ротация файлов**: 10 MB, 5 бэкапов
- **Формат**: Строковый формат с ISO timestamp

Просмотр логов:
```bash
tail -f logs/actions.log
```

## Технологии

- **Python 3.11+**: Основной язык программирования
- **Poetry**: Управление зависимостями
- **Ruff**: Статический анализ и форматирование кода
- **PrettyTable**: Форматированный вывод таблиц
- **Requests**: HTTP-запросы к внешним API
- **JSON**: Хранение данных

## Структура данных

### users.json
```json
[
  {
    "user_id": 1,
    "username": "alice",
    "hashed_password": "3e2a19...",
    "salt": "x5T9!",
    "registration_date": "2025-10-09T12:00:00"
  }
]
```

### portfolios.json
```json
[
  {
    "user_id": 1,
    "wallets": {
      "USD": {"balance": 1500.0},
      "BTC": {"balance": 0.05},
      "EUR": {"balance": 200.0}
    }
  }
]
```

### rates.json (кеш для Core Service)
```json
{
  "pairs": {
    "BTC_USD": {
      "rate": 59337.21,
      "updated_at": "2025-10-09T12:00:00Z",
      "source": "CoinGecko"
    }
  },
  "last_refresh": "2025-10-09T12:00:00Z"
}
```

### exchange_rates.json (исторический журнал)
```json
{
  "records": [
    {
      "id": "BTC_USD_2025-10-09T12:00:00Z",
      "from_currency": "BTC",
      "to_currency": "USD",
      "rate": 59337.21,
      "timestamp": "2025-10-09T12:00:00Z",
      "source": "CoinGecko",
      "meta": {
        "request_ms": 124,
        "status_code": 200
      }
    }
  ]
}
```

## Особенности реализации

- **Объектно-ориентированное программирование**: Использование классов и наследования
- **Паттерн Singleton**: SettingsLoader и DatabaseManager
- **Декораторы**: @log_action для логирования операций
- **Обработка исключений**: Пользовательские исключения с понятными сообщениями
- **Валидация данных**: Проверка входных данных на всех уровнях
- **Атомарные операции**: Безопасная запись в файлы через временные файлы

## Лицензия

Этот проект создан в учебных целях.
