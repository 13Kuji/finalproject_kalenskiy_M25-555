"""Бизнес-логика приложения."""

from datetime import datetime, timedelta

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    InsufficientFundsError,
    RateUnavailableError,
    WalletNotFoundError,
)
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    ensure_data_dir,
    load_json,
    save_json,
    validate_currency_code,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import settings


class UserManager:
    """Менеджер для работы с пользователями."""

    def __init__(self) -> None:
        """Инициализация менеджера пользователей."""
        ensure_data_dir()
        self._users: dict[int, User] = {}
        self._load_users()

    def _load_users(self) -> None:
        """Загрузить пользователей из JSON файла."""
        users_data = load_json("users.json")

        for user_data in users_data:
            user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                hashed_password=user_data["hashed_password"],
                salt=user_data["salt"],
                registration_date=datetime.fromisoformat(
                    user_data["registration_date"]
                ),
            )
            self._users[user.user_id] = user

    def _save_users(self) -> None:
        """Сохранить пользователей в JSON файл."""
        users_data = []

        for user in self._users.values():
            users_data.append(
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "hashed_password": user.hashed_password,
                    "salt": user.salt,
                    "registration_date": user.registration_date.isoformat(),
                }
            )

        save_json("users.json", users_data)

    @log_action("REGISTER")
    def create_user(self, username: str, password: str) -> User:
        """
        Создать нового пользователя.

        Args:
            username: Имя пользователя
            password: Пароль пользователя

        Returns:
            Созданный объект User

        Raises:
            ValueError: Если пользователь с таким именем уже существует
        """
        # Проверяем уникальность имени
        for user in self._users.values():
            if user.username == username:
                raise ValueError(
                    f"Пользователь с именем '{username}' уже существует"
                )

        # Генерируем новый ID
        user_id = max(self._users.keys(), default=0) + 1

        # Создаём пользователя
        hashed_password, salt = User.hash_password(password)
        user = User(
            user_id=user_id,
            username=username,
            hashed_password=hashed_password,
            salt=salt,
            registration_date=datetime.now(),
        )

        self._users[user_id] = user
        self._save_users()

        return user

    def get_user(self, user_id: int) -> User | None:
        """
        Получить пользователя по ID.

        Args:
            user_id: ID пользователя

        Returns:
            Объект User или None
        """
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        """
        Получить пользователя по имени.

        Args:
            username: Имя пользователя

        Returns:
            Объект User или None
        """
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    @log_action("LOGIN")
    def authenticate(self, username: str, password: str) -> User | None:
        """
        Аутентифицировать пользователя.

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            Объект User если аутентификация успешна, иначе None
        """
        user = self.get_user_by_username(username)
        if user and user.verify_password(password):
            return user
        return None


class PortfolioManager:
    """Менеджер для работы с портфелями."""

    def __init__(self, user_manager: UserManager) -> None:
        """
        Инициализация менеджера портфелей.

        Args:
            user_manager: Менеджер пользователей
        """
        ensure_data_dir()
        self._user_manager = user_manager
        self._portfolios: dict[int, Portfolio] = {}
        self._load_portfolios()

    def _load_portfolios(self) -> None:
        """Загрузить портфели из JSON файла."""
        portfolios_data = load_json("portfolios.json")

        for portfolio_data in portfolios_data:
            user_id = portfolio_data["user_id"]
            wallets_dict: dict[str, Wallet] = {}

            for (
                currency_code,
                wallet_data,
            ) in portfolio_data["wallets"].items():
                wallet = Wallet(
                    currency_code=currency_code,
                    balance=wallet_data.get("balance", 0.0),
                )
                wallets_dict[currency_code] = wallet

            portfolio = Portfolio(
                user_id=user_id, wallets=wallets_dict
            )
            # Связываем с пользователем, если он существует
            user = self._user_manager.get_user(user_id)
            if user:
                portfolio.set_user(user)

            self._portfolios[user_id] = portfolio

    def _save_portfolios(self) -> None:
        """Сохранить портфели в JSON файл."""
        portfolios_data = []

        for portfolio in self._portfolios.values():
            wallets_dict = {}

            for currency_code, wallet in portfolio.wallets.items():
                wallets_dict[currency_code] = {
                    "currency_code": currency_code,
                    "balance": wallet.balance,
                }

            portfolios_data.append(
                {
                    "user_id": portfolio.user_id,
                    "wallets": wallets_dict,
                }
            )

        save_json("portfolios.json", portfolios_data)

    def get_portfolio(self, user_id: int) -> Portfolio:
        """
        Получить портфель пользователя (создать, если не существует).

        Args:
            user_id: ID пользователя

        Returns:
            Объект Portfolio
        """
        if user_id not in self._portfolios:
            portfolio = Portfolio(user_id=user_id)
            user = self._user_manager.get_user(user_id)
            if user:
                portfolio.set_user(user)
            self._portfolios[user_id] = portfolio
            self._save_portfolios()

        return self._portfolios[user_id]

    def save_portfolio(self, portfolio: Portfolio) -> None:
        """
        Сохранить портфель.

        Args:
            portfolio: Объект портфеля для сохранения
        """
        self._portfolios[portfolio.user_id] = portfolio
        self._save_portfolios()

    @log_action("BUY", verbose=True)
    def buy_currency(
        self,
        user_id: int,
        currency: str,
        amount: float,
        rate_manager: "RateManager",
    ) -> tuple[float, float]:
        """
        Купить валюту (увеличить баланс).

        Args:
            user_id: ID пользователя
            currency: Код покупаемой валюты
            amount: Количество валюты
            rate_manager: Менеджер курсов

        Returns:
            Кортеж (курс, стоимость в USD)

        Raises:
            InvalidCurrencyCodeError: Если код валюты некорректен
            CurrencyNotFoundError: Если валюта не найдена в реестре
            RateUnavailableError: Если курс недоступен
            ValueError: Если сумма некорректна
        """
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        # Валидация и проверка валюты
        currency_code = validate_currency_code(currency)
        get_currency(currency_code)  # Проверка существования валюты

        portfolio = self.get_portfolio(user_id)

        # Получаем курс для расчета стоимости
        try:
            rate = rate_manager.get_or_fetch_rate(currency_code, "USD")
        except ApiRequestError:
            # Пробрасываем ApiRequestError как RateUnavailableError
            raise RateUnavailableError(currency_code, "USD") from None

        # Добавляем валюту, если её нет
        if currency_code not in portfolio.wallets:
            portfolio.add_currency(currency_code)

        wallet = portfolio.get_wallet(currency_code)
        if wallet is None:
            raise ValueError(
                f"Не удалось создать кошелёк {currency_code}"
            )

        wallet.deposit(amount)
        self.save_portfolio(portfolio)

        # Стоимость в USD
        cost_usd = amount * rate

        return rate, cost_usd

    @log_action("SELL", verbose=True)
    def sell_currency(
        self,
        user_id: int,
        currency: str,
        amount: float,
        rate_manager: "RateManager",
    ) -> tuple[float, float]:
        """
        Продать валюту (уменьшить баланс).

        Args:
            user_id: ID пользователя
            currency: Код продаваемой валюты
            amount: Количество валюты
            rate_manager: Менеджер курсов

        Returns:
            Кортеж (курс, выручка в USD)

        Raises:
            InvalidCurrencyCodeError: Если код валюты некорректен
            CurrencyNotFoundError: Если валюта не найдена в реестре
            WalletNotFoundError: Если кошелёк не найден
            InsufficientFundsError: Если недостаточно средств
            RateUnavailableError: Если курс недоступен
            ValueError: Если сумма некорректна
        """
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        # Валидация и проверка валюты
        currency_code = validate_currency_code(currency)
        get_currency(currency_code)  # Проверка существования валюты

        portfolio = self.get_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)

        if wallet is None:
            raise WalletNotFoundError(currency_code)

        old_balance = wallet.balance

        # Проверяем баланс
        if amount > old_balance:
            raise InsufficientFundsError(
                currency_code, old_balance, amount
            )

        # Получаем курс для расчета выручки
        try:
            rate = rate_manager.get_or_fetch_rate(currency_code, "USD")
        except ApiRequestError:
            # Пробрасываем ApiRequestError как RateUnavailableError
            raise RateUnavailableError(currency_code, "USD") from None

        wallet.withdraw(amount)
        self.save_portfolio(portfolio)

        # Выручка в USD
        revenue_usd = amount * rate

        return rate, revenue_usd


class RateManager:
    """Менеджер для работы с курсами валют."""

    def __init__(self) -> None:
        """Инициализация менеджера курсов."""
        ensure_data_dir()
        self._rates: dict[str, dict] = {}
        self._load_rates()

    def _load_rates(self) -> None:
        """Загрузить курсы из JSON файла."""
        rates_data = load_json("rates.json")
        # Убираем служебные поля из основного словаря
        self._rates = {
            k: v for k, v in rates_data.items()
            if k not in ("source", "last_refresh")
        }

    def _save_rates(self, source: str = "ParserService") -> None:
        """Сохранить курсы в JSON файл."""
        rates_data = self._rates.copy()
        rates_data["source"] = source
        rates_data["last_refresh"] = datetime.now().isoformat()
        save_json("rates.json", rates_data)

    def get_rate(self, from_currency: str, to_currency: str) -> float | None:
        """
        Получить курс обмена между валютами.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта

        Returns:
            Курс обмена или None если не найден
        """
        # Если валюты одинаковые
        if from_currency == to_currency:
            return 1.0

        # Прямой курс (например, BTC_USD)
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in self._rates:
            return float(self._rates[rate_key]["rate"])

        # Обратный курс (например, USD_BTC)
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in self._rates:
            return 1.0 / float(self._rates[reverse_key]["rate"])

        return None

    def is_rate_fresh(
        self, from_currency: str, to_currency: str,
        max_age_seconds: int | None = None
    ) -> bool:
        """
        Проверить, свежий ли курс (не старше max_age_seconds).

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            max_age_seconds: Максимальный возраст курса в секундах
                (по умолчанию из settings)

        Returns:
            True если курс свежий, False иначе
        """
        if from_currency == to_currency:
            return True

        max_age = max_age_seconds or settings.rates_ttl_seconds

        rate_key = f"{from_currency}_{to_currency}"
        if rate_key not in self._rates:
            reverse_key = f"{to_currency}_{from_currency}"
            if reverse_key not in self._rates:
                return False
            rate_key = reverse_key

        updated_at_str = self._rates[rate_key].get("updated_at")
        if not updated_at_str:
            return False

        try:
            updated_at = datetime.fromisoformat(updated_at_str)
            age = datetime.now() - updated_at
            return age <= timedelta(seconds=max_age)
        except (ValueError, TypeError):
            return False

    def update_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        source: str = "ParserService",
    ) -> None:
        """
        Обновить курс валют.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            rate: Курс обмена
            source: Источник курса
        """
        rate_key = f"{from_currency}_{to_currency}"
        self._rates[rate_key] = {
            "rate": rate,
            "updated_at": datetime.now().isoformat(),
        }
        self._save_rates(source)

    def get_fallback_rate(
        self, from_currency: str, to_currency: str
    ) -> float | None:
        """
        Получить курс из заглушки (фиксированные курсы).

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта

        Returns:
            Курс обмена или None
        """
        # Фиксированные курсы для заглушки
        fallback_rates: dict[str, dict[str, float]] = {
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

        if from_currency in fallback_rates:
            if to_currency in fallback_rates[from_currency]:
                return fallback_rates[from_currency][to_currency]

        return None

    def get_or_fetch_rate(
        self, from_currency: str, to_currency: str
    ) -> float | None:
        """
        Получить курс (из кеша или заглушки).

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта

        Returns:
            Курс обмена или None

        Raises:
            ApiRequestError: Если курс недоступен и API не отвечает
        """
        # Проверяем кеш
        rate = self.get_rate(from_currency, to_currency)
        if rate is not None and self.is_rate_fresh(
            from_currency, to_currency
        ):
            return rate

        # Попытка получить курс из заглушки/API
        try:
            fallback_rate = self.get_fallback_rate(from_currency, to_currency)
            if fallback_rate is not None:
                self.update_rate(from_currency, to_currency, fallback_rate)
                return fallback_rate
        except Exception as e:
            # При ошибке обращения к API выбрасываем ApiRequestError
            raise ApiRequestError(
                f"Не удалось получить курс {from_currency}→{to_currency}: {e}"
            ) from e

        # Если курс недоступен
        raise ApiRequestError(
            f"Курс {from_currency}→{to_currency} недоступен"
        )

