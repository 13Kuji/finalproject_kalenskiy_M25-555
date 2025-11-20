"""Основные классы моделей приложения."""

import hashlib
import secrets
from datetime import datetime


class User:
    """Класс пользователя системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        """
        Инициализация пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя
            username: Имя пользователя
            hashed_password: Зашифрованный пароль
            salt: Уникальная соль для пароля
            registration_date: Дата регистрации
        """
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Геттер для user_id."""
        return self._user_id

    @property
    def username(self) -> str:
        """Геттер для username."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Сеттер для username с проверкой."""
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        """Геттер для hashed_password."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Геттер для salt."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Геттер для registration_date."""
        return self._registration_date

    def get_user_info(self) -> dict:
        """
        Получить информацию о пользователе (без пароля).

        Returns:
            Словарь с информацией о пользователе
        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """
        Изменить пароль пользователя.

        Args:
            new_password: Новый пароль пользователя

        Raises:
            ValueError: Если пароль короче 4 символов
        """
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        # Генерируем новую соль или используем существующую
        if not self._salt:
            self._salt = secrets.token_hex(8)

        # Хешируем пароль с солью
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """
        Проверить введённый пароль на совпадение.

        Args:
            password: Пароль для проверки

        Returns:
            True если пароль верный, False иначе
        """
        hashed_input = hashlib.sha256(
            (password + self._salt).encode()
        ).hexdigest()
        return hashed_input == self._hashed_password

    @staticmethod
    def hash_password(
        password: str, salt: str | None = None
    ) -> tuple[str, str]:
        """
        Хешировать пароль с солью.

        Args:
            password: Пароль для хеширования
            salt: Соль (если None, генерируется новая)

        Returns:
            Кортеж (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(8)

        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed, salt


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """
        Инициализация кошелька.

        Args:
            currency_code: Код валюты (например, "USD", "BTC")
            balance: Начальный баланс (по умолчанию 0.0)
        """
        self.currency_code = currency_code
        # Гарантируем неотрицательность
        self._balance = max(0.0, float(balance))

    @property
    def balance(self) -> float:
        """Геттер для balance."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Сеттер для balance с проверкой."""
        try:
            float_value = float(value)
            if float_value < 0:
                raise ValueError(
                    "Баланс не может быть отрицательным"
                )
            self._balance = float_value
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Некорректное значение баланса: {e}"
            ) from e

    def deposit(self, amount: float) -> None:
        """
        Пополнение баланса.

        Args:
            amount: Сумма пополнения

        Raises:
            ValueError: Если сумма отрицательная или некорректная
        """
        try:
            float_amount = float(amount)
            if float_amount <= 0:
                raise ValueError("Сумма пополнения должна быть положительной")
            self._balance += float_amount
        except (TypeError, ValueError) as e:
            raise ValueError(f"Некорректная сумма: {e}") from e

    def withdraw(self, amount: float) -> None:
        """
        Снятие средств.

        Args:
            amount: Сумма снятия

        Raises:
            ValueError: Если сумма превышает баланс или отрицательная
        """
        try:
            float_amount = float(amount)
            if float_amount <= 0:
                raise ValueError("Сумма снятия должна быть положительной")
            if float_amount > self._balance:
                raise ValueError(
                    f"Недостаточно средств. "
                    f"Текущий баланс: {self._balance}, "
                    f"запрошено: {float_amount}"
                )
            self._balance -= float_amount
        except (TypeError, ValueError) as e:
            raise ValueError(f"Некорректная сумма: {e}") from e

    def get_balance_info(self) -> dict:
        """
        Получить информацию о текущем балансе.

        Returns:
            Словарь с информацией о балансе
        """
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }


class Portfolio:
    """Управление всеми кошельками одного пользователя."""

    def __init__(
        self, user_id: int, wallets: dict[str, Wallet] | None = None
    ) -> None:
        """
        Инициализация портфеля.

        Args:
            user_id: Уникальный идентификатор пользователя
            wallets: Словарь кошельков (ключ - код валюты, значение - Wallet)
        """
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = (
            wallets.copy() if wallets else {}
        )
        self._user: User | None = None

    @property
    def user_id(self) -> int:
        """Геттер для user_id."""
        return self._user_id

    @property
    def user(self) -> User | None:
        """Геттер для объекта пользователя (без возможности перезаписи)."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Геттер, возвращающий копию словаря кошельков."""
        return self._wallets.copy()

    def set_user(self, user: User) -> None:
        """
        Установить объект пользователя.

        Args:
            user: Объект пользователя
        """
        if user.user_id != self._user_id:
            raise ValueError(
                "ID пользователя не совпадает с ID портфеля"
            )
        self._user = user

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавить новый кошелёк в портфель.

        Args:
            currency_code: Код валюты

        Returns:
            Созданный объект Wallet

        Raises:
            ValueError: Если кошелёк с такой валютой уже существует
        """
        if currency_code in self._wallets:
            raise ValueError(
                f"Кошелёк с валютой {currency_code} уже существует в портфеле"
            )

        wallet = Wallet(currency_code=currency_code, balance=0.0)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """
        Получить объект Wallet по коду валюты.

        Args:
            currency_code: Код валюты

        Returns:
            Объект Wallet или None если не найден
        """
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = "USD") -> float:
        """
        Получить общую стоимость всех валют в указанной базовой валюте.

        Args:
            base_currency: Базовая валюта для конвертации
                (по умолчанию USD)

        Returns:
            Общая стоимость портфеля в базовой валюте

        Note:
            Этот метод использует фиксированные курсы.
            Для реальных курсов используйте PortfolioManager
            с RateManager.
        """
        # Фиксированные курсы обмена (для упрощения)
        # В реальном приложении эти курсы будут получаться из API
        exchange_rates: dict[str, dict[str, float]] = {
            "USD": {
                "USD": 1.0,
                "EUR": 0.92,
                "BTC": 0.000023,
                "ETH": 0.00035,
                "RUB": 92.0,
            },
            "EUR": {
                "USD": 1.09,
                "EUR": 1.0,
                "BTC": 0.000025,
                "ETH": 0.00038,
                "RUB": 100.0,
            },
            "BTC": {
                "USD": 43500.0,
                "EUR": 40000.0,
                "BTC": 1.0,
                "ETH": 15.5,
                "RUB": 4002000.0,
            },
            "ETH": {
                "USD": 2800.0,
                "EUR": 2576.0,
                "BTC": 0.064,
                "ETH": 1.0,
                "RUB": 257600.0,
            },
            "RUB": {
                "USD": 0.011,
                "EUR": 0.01,
                "BTC": 0.00000025,
                "ETH": 0.0000039,
                "RUB": 1.0,
            },
        }

        total_value = 0.0

        # Если базовая валюта отсутствует в курсах, возвращаем 0
        if base_currency not in exchange_rates:
            return 0.0

        base_rates = exchange_rates[base_currency]

        for currency_code, wallet in self._wallets.items():
            if currency_code == base_currency:
                # Если валюта совпадает с базовой, добавляем баланс как есть
                total_value += wallet.balance
            elif currency_code in base_rates:
                # Конвертируем в базовую валюту
                rate = base_rates[currency_code]
                total_value += wallet.balance * rate
            # Если курс не найден, пропускаем эту валюту

        return total_value

