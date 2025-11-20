"""Пользовательские исключения приложения."""


class ValutaTradeError(Exception):
    """Базовое исключение приложения."""

    pass


class CurrencyNotFoundError(ValutaTradeError):
    """Исключение: неизвестная валюта."""

    def __init__(self, currency_code: str) -> None:
        """
        Инициализация исключения.

        Args:
            currency_code: Код валюты, которая не найдена
        """
        self.currency_code = currency_code
        super().__init__(f"Неизвестная валюта '{currency_code}'")


class InvalidCurrencyCodeError(ValutaTradeError):
    """Исключение: некорректный код валюты."""

    def __init__(self, currency_code: str, reason: str = "") -> None:
        """
        Инициализация исключения.

        Args:
            currency_code: Некорректный код валюты
            reason: Причина ошибки
        """
        self.currency_code = currency_code
        message = f"Некорректный код валюты '{currency_code}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class InsufficientFundsError(ValutaTradeError):
    """Исключение: недостаточно средств."""

    def __init__(
        self, currency: str, available: float, required: float
    ) -> None:
        """
        Инициализация исключения.

        Args:
            currency: Код валюты
            available: Доступный баланс
            required: Требуемая сумма
        """
        self.currency = currency
        self.available = available
        self.required = required
        super().__init__(
            f"Недостаточно средств: доступно {available} {currency}, "
            f"требуется {required} {currency}"
        )


class ApiRequestError(ValutaTradeError):
    """Исключение: сбой внешнего API."""

    def __init__(self, reason: str) -> None:
        """
        Инициализация исключения.

        Args:
            reason: Причина ошибки API
        """
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class RateUnavailableError(ValutaTradeError):
    """Исключение: курс валют недоступен."""

    def __init__(self, from_currency: str, to_currency: str) -> None:
        """
        Инициализация исключения.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
        """
        self.from_currency = from_currency
        self.to_currency = to_currency
        super().__init__(
            f"Курс {from_currency}→{to_currency} недоступен. "
            f"Повторите попытку позже."
        )


class WalletNotFoundError(ValutaTradeError):
    """Исключение: кошелёк не найден."""

    def __init__(self, currency_code: str) -> None:
        """
        Инициализация исключения.

        Args:
            currency_code: Код валюты
        """
        self.currency_code = currency_code
        super().__init__(
            f"У вас нет кошелька '{currency_code}'. "
            f"Добавьте валюту: она создаётся автоматически "
            f"при первой покупке."
        )

