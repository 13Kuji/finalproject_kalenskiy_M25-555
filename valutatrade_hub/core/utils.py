"""Вспомогательные функции для работы с данными."""

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.core.currencies import Currency, get_currency
from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InvalidCurrencyCodeError,
)

# Базовый путь к директории с данными
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load_json(file_name: str) -> Any:
    """
    Загрузить данные из JSON файла.

    Args:
        file_name: Имя файла в директории data/

    Returns:
        Загруженные данные (dict или list)

    Raises:
        FileNotFoundError: Если файл не найден
        json.JSONDecodeError: Если файл содержит некорректный JSON
    """
    file_path = DATA_DIR / file_name

    if not file_path.exists():
        # Если файл не существует, возвращаем значение по умолчанию
        if file_name.endswith(".json"):
            if "rates" in file_name:
                return {}
            return []
        return {}

    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def save_json(file_name: str, data: Any) -> None:
    """
    Сохранить данные в JSON файл.

    Args:
        file_name: Имя файла в директории data/
        data: Данные для сохранения (должны быть сериализуемы в JSON)

    Raises:
        json.JSONEncodeError: Если данные не могут быть сериализованы
    """
    file_path = DATA_DIR / file_name

    # Создаём директорию, если её нет
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_data_dir() -> None:
    """Убедиться, что директория data/ существует."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Путь к файлу сессии
SESSION_FILE = DATA_DIR.parent / ".session.json"


def load_session() -> dict | None:
    """
    Загрузить сессию из файла.

    Returns:
        Данные сессии или None
    """
    if not SESSION_FILE.exists():
        return None

    try:
        with open(SESSION_FILE, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return None
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None


def save_session(session_data: dict) -> None:
    """
    Сохранить сессию в файл.

    Args:
        session_data: Данные сессии
    """
    # Сохраняем в родительскую директорию (корень проекта)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)


def clear_session() -> None:
    """Очистить сессию."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def validate_currency_code(currency_code: str) -> str:
    """
    Валидировать код валюты и нормализовать его.

    Args:
        currency_code: Код валюты для валидации

    Returns:
        Нормализованный код валюты (верхний регистр)

    Raises:
        InvalidCurrencyCodeError: Если код некорректен
    """
    if not currency_code or not currency_code.strip():
        raise InvalidCurrencyCodeError(
            currency_code or "", "код валюты не может быть пустым"
        )

    code_clean = currency_code.strip().upper()

    # Используем валидацию из Currency
    Currency._validate_code(code_clean)

    return code_clean


def normalize_currency_code(currency_code: str) -> str:
    """
    Нормализовать код валюты (верхний регистр, без пробелов).

    Args:
        currency_code: Код валюты

    Returns:
        Нормализованный код
    """
    return currency_code.strip().upper()


def get_currency_info(currency_code: str) -> str:
    """
    Получить информацию о валюте для отображения.

    Args:
        currency_code: Код валюты

    Returns:
        Строка с информацией о валюте

    Raises:
        CurrencyNotFoundError: Если валюта не найдена
    """
    try:
        currency = get_currency(currency_code)
        return currency.get_display_info()
    except CurrencyNotFoundError:
        raise

