"""Модели валют с иерархией наследования."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InvalidCurrencyCodeError,
)


class Currency(ABC):
    """Абстрактный базовый класс валюты."""

    def __init__(self, name: str, code: str) -> None:
        """
        Инициализация валюты.

        Args:
            name: Человекочитаемое имя валюты
            code: ISO-код или тикер валюты

        Raises:
            InvalidCurrencyCodeError: Если код валюты некорректен
        """
        if not name or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")

        self._validate_code(code)

        self.name = name.strip()
        self.code = code.strip().upper()

    @staticmethod
    def _validate_code(code: str) -> None:
        """
        Валидировать код валюты.

        Args:
            code: Код валюты

        Raises:
            InvalidCurrencyCodeError: Если код некорректен
        """
        if not code or not code.strip():
            raise InvalidCurrencyCodeError(
                code or "", "код валюты не может быть пустым"
            )

        code_clean = code.strip().upper()

        if len(code_clean) < 2 or len(code_clean) > 5:
            raise InvalidCurrencyCodeError(
                code, "код должен содержать от 2 до 5 символов"
            )

        if " " in code_clean:
            raise InvalidCurrencyCodeError(
                code, "код не должен содержать пробелы"
            )

        if not code_clean.isalnum():
            raise InvalidCurrencyCodeError(
                code, "код должен содержать только буквы и цифры"
            )

    @abstractmethod
    def get_display_info(self) -> str:
        """
        Получить строковое представление валюты для UI/логов.

        Returns:
            Форматированная строка с информацией о валюте
        """
        pass

    def __str__(self) -> str:
        """Строковое представление валюты."""
        return f"{self.code} — {self.name}"

    def __repr__(self) -> str:
        """Представление валюты для разработчиков."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"code='{self.code}')"
        )

    def __eq__(self, other: object) -> bool:
        """Проверка равенства валют по коду."""
        if not isinstance(other, Currency):
            return False
        return self.code == other.code

    def __hash__(self) -> int:
        """Хеш валюты для использования в словарях и множествах."""
        return hash(self.code)


class FiatCurrency(Currency):
    """Фиатная валюта (традиционная валюта)."""

    def __init__(
        self, name: str, code: str, issuing_country: str
    ) -> None:
        """
        Инициализация фиатной валюты.

        Args:
            name: Человекочитаемое имя валюты
            code: ISO-код валюты (обычно 3 символа)
            issuing_country: Страна или зона эмиссии валюты
        """
        super().__init__(name, code)

        if not issuing_country or not issuing_country.strip():
            raise ValueError(
                "Страна/зона эмиссии не может быть пустой"
            )

        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """
        Получить строковое представление фиатной валюты.

        Returns:
            Форматированная строка: "[FIAT] CODE — Name (Issuing: Country)"
        """
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float = 0.0,
    ) -> None:
        """
        Инициализация криптовалюты.

        Args:
            name: Человекочитаемое имя валюты
            code: Тикер криптовалюты (обычно 2-5 символов)
            algorithm: Алгоритм консенсуса или хеширования
            market_cap: Рыночная капитализация (по умолчанию 0.0)
        """
        super().__init__(name, code)

        if not algorithm or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")

        if market_cap < 0:
            raise ValueError(
                "Рыночная капитализация не может быть отрицательной"
            )

        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """
        Получить строковое представление криптовалюты.

        Returns:
            Форматированная строка: "[CRYPTO] CODE — Name "
            "(Algo: Algorithm, MCAP: MarketCap)"
        """
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap > 0 else "N/A"
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {mcap_str})"
        )


# Реестр валют
_CURRENCY_REGISTRY: dict[str, Currency] = {}


def _initialize_registry() -> None:
    """Инициализировать реестр валют предопределёнными значениями."""
    global _CURRENCY_REGISTRY

    # Фиатные валюты
    fiat_currencies = [
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        FiatCurrency("British Pound", "GBP", "United Kingdom"),
        FiatCurrency("Japanese Yen", "JPY", "Japan"),
        FiatCurrency("Swiss Franc", "CHF", "Switzerland"),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        FiatCurrency("Chinese Yuan", "CNY", "China"),
        FiatCurrency("Canadian Dollar", "CAD", "Canada"),
        FiatCurrency("Australian Dollar", "AUD", "Australia"),
    ]

    # Криптовалюты
    crypto_currencies = [
        CryptoCurrency(
            "Bitcoin", "BTC", "SHA-256", market_cap=1.12e12
        ),
        CryptoCurrency(
            "Ethereum", "ETH", "Ethash", market_cap=4.5e11
        ),
        CryptoCurrency("Litecoin", "LTC", "Scrypt", market_cap=5.5e9),
        CryptoCurrency("Ripple", "XRP", "XRP Ledger", market_cap=3.2e10),
        CryptoCurrency(
            "Cardano", "ADA", "Ouroboros", market_cap=1.5e10
        ),
        CryptoCurrency(
            "Polkadot",
            "DOT",
            "Nominated Proof-of-Stake",
            market_cap=7.5e9,
        ),
    ]

    for currency in fiat_currencies + crypto_currencies:
        _CURRENCY_REGISTRY[currency.code] = currency


def get_currency(code: str) -> Currency:
    """
    Получить валюту по коду из реестра.

    Args:
        code: Код валюты

    Returns:
        Объект Currency

    Raises:
        InvalidCurrencyCodeError: Если код некорректен
        CurrencyNotFoundError: Если валюта не найдена в реестре
    """
    if not _CURRENCY_REGISTRY:
        _initialize_registry()

    # Валидация кода
    code_clean = code.strip().upper()
    Currency._validate_code(code_clean)

    # Поиск в реестре
    if code_clean not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code_clean)

    return _CURRENCY_REGISTRY[code_clean]


def register_currency(currency: Currency) -> None:
    """
    Зарегистрировать валюту в реестре.

    Args:
        currency: Объект валюты для регистрации
    """
    if not _CURRENCY_REGISTRY:
        _initialize_registry()

    _CURRENCY_REGISTRY[currency.code] = currency


def list_currencies(currency_type: type | None = None) -> list[Currency]:
    """
    Получить список всех валют в реестре.

    Args:
        currency_type: Тип валюты для фильтрации (None = все)

    Returns:
        Список валют
    """
    if not _CURRENCY_REGISTRY:
        _initialize_registry()

    currencies = list(_CURRENCY_REGISTRY.values())

    if currency_type is None:
        return currencies

    return [
        curr for curr in currencies if isinstance(curr, currency_type)
    ]

