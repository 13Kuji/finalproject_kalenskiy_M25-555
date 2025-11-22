"""Конфигурация Parser Service."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import settings


def load_env_file() -> None:
    """Загрузить переменные окружения из .env файла (если существует)."""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass  # Игнорируем ошибки чтения .env


# Загружаем .env файл при импорте модуля
load_env_file()


def get_env_key(key: str, default: str = "") -> str:
    """
    Получить значение переменной окружения.

    Args:
        key: Имя переменной окружения
        default: Значение по умолчанию

    Returns:
        Значение переменной окружения
    """
    # Сначала загружаем .env, если он есть
    load_env_file()
    return os.getenv(key, default)


@dataclass
class ParserConfig:
    """Конфигурация для Parser Service."""

    # API ключи (загружаются из переменных окружения или .env файла)
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: get_env_key("EXCHANGERATE_API_KEY", "")
    )

    # Эндпоинты API
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Базовая валюта для запросов
    BASE_CURRENCY: str = "USD"

    # Списки валют для отслеживания
    FIAT_CURRENCIES: tuple[str, ...] = (
        "EUR",
        "GBP",
        "RUB",
        "JPY",
        "CHF",
        "CNY",
        "CAD",
        "AUD",
    )

    CRYPTO_CURRENCIES: tuple[str, ...] = (
        "BTC",
        "ETH",
        "SOL",
        "LTC",
        "XRP",
        "ADA",
        "DOT",
    )

    # Сопоставление кодов криптовалют и ID для CoinGecko
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "LTC": "litecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOT": "polkadot",
        }
    )

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10  # секунды

    # Пути к файлам
    @property
    def rates_file_path(self) -> Path:  # noqa: N802
        """Путь к файлу rates.json (кеш для Core Service)."""
        return settings.data_dir / "rates.json"

    @property
    def history_file_path(self) -> Path:  # noqa: N802
        """Путь к файлу exchange_rates.json (исторический журнал)."""
        return settings.data_dir / "exchange_rates.json"

    def validate(self) -> None:
        """
        Валидировать конфигурацию.

        Raises:
            ValueError: Если конфигурация некорректна
        """
        if not self.EXCHANGERATE_API_KEY:
            raise ValueError(
                "EXCHANGERATE_API_KEY не установлен. "
                "Установите переменную окружения или "
                "добавьте ключ в config."
            )


# Глобальный экземпляр конфигурации
config = ParserConfig()

