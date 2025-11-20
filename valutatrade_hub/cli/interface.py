"""Командный интерфейс приложения."""
from __future__ import annotations

import argparse
import sys

from valutatrade_hub.core.currencies import list_currencies
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    RateUnavailableError,
    WalletNotFoundError,
)
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    PortfolioManager,
    RateManager,
    UserManager,
)
from valutatrade_hub.core.utils import (
    clear_session,
    load_session,
    save_session,
)
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def _validate_currency(currency: str) -> str:
    """
    Валидировать код валюты.

    Args:
        currency: Код валюты

    Returns:
        Код валюты в верхнем регистре

    Raises:
        ValueError: Если валюта некорректна
    """
    if not currency or not currency.strip():
        raise ValueError("Код валюты не может быть пустым")
    return currency.strip().upper()


class CLIInterface:
    """Командный интерфейс для взаимодействия с пользователем."""

    def __init__(self) -> None:
        """Инициализация интерфейса."""
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
        self.rate_manager = RateManager()
        self.current_user: User | None = self._load_session()

    def _load_session(self) -> User | None:
        """
        Загрузить текущую сессию.

        Returns:
            Объект User или None
        """
        session = load_session()
        if session is None:
            return None

        user_id = session.get("user_id")
        if user_id is None:
            return None

        return self.user_manager.get_user(user_id)

    def _save_session(self) -> None:
        """Сохранить текущую сессию."""
        if self.current_user is None:
            clear_session()
        else:
            save_session({"user_id": self.current_user.user_id})

    def _clear_session(self) -> None:
        """Очистить текущую сессию."""
        self.current_user = None
        clear_session()

    def _validate_amount(self, amount: float) -> float:
        """
        Валидировать сумму.

        Args:
            amount: Сумма

        Returns:
            Валидная сумма

        Raises:
            ValueError: Если сумма некорректна
        """
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        return float(amount)

    def _require_login(self) -> None:
        """
        Проверить, что пользователь залогинен.

        Raises:
            SystemExit: Если пользователь не залогинен
        """
        if self.current_user is None:
            print("Сначала выполните login", file=sys.stderr)
            sys.exit(1)

    def register(self, username: str, password: str) -> None:
        """
        Зарегистрировать нового пользователя.

        Args:
            username: Имя пользователя
            password: Пароль
        """
        if not username or not username.strip():
            print("Имя пользователя не может быть пустым", file=sys.stderr)
            sys.exit(1)

        if len(password) < 4:
            print(
                "Пароль должен быть не короче 4 символов",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            user = self.user_manager.create_user(username, password)
            # Создаём пустой портфель
            self.portfolio_manager.get_portfolio(user.user_id)
            print(
                f"Пользователь '{user.username}' зарегистрирован "
                f"(id={user.user_id}). Войдите: "
                f"login --username {user.username} --password ****"
            )
        except ValueError as e:
            error_msg = str(e)
            if "уже существует" in error_msg:
                print(
                    f"Имя пользователя '{username}' уже занято",
                    file=sys.stderr,
                )
            else:
                print(f"Ошибка: {e}", file=sys.stderr)
            sys.exit(1)

    def login(self, username: str, password: str) -> None:
        """
        Войти в систему.

        Args:
            username: Имя пользователя
            password: Пароль
        """
        user = self.user_manager.authenticate(username, password)

        if user is None:
            # Проверяем, существует ли пользователь
            if self.user_manager.get_user_by_username(username) is None:
                print(
                    f"Пользователь '{username}' не найден",
                    file=sys.stderr,
                )
            else:
                print("Неверный пароль", file=sys.stderr)
            sys.exit(1)

        self.current_user = user
        self._save_session()
        print(f"Вы вошли как '{user.username}'")

    def show_portfolio(self, base: str = "USD") -> None:
        """
        Показать портфель пользователя.

        Args:
            base: Базовая валюта (по умолчанию USD)
        """
        self._require_login()

        base = _validate_currency(base)
        portfolio = self.portfolio_manager.get_portfolio(
            self.current_user.user_id
        )
        wallets = portfolio.wallets

        if not wallets:
            print("У вас пока нет кошельков.")
            return

        print(f"\nПортфель пользователя '{self.current_user.username}' "
              f"(база: {base}):")

        total_value = 0.0

        for currency_code, wallet in sorted(wallets.items()):
            balance = wallet.balance

            if currency_code == base:
                value_in_base = balance
            else:
                rate = self.rate_manager.get_or_fetch_rate(
                    currency_code, base
                )
                if rate is None:
                    print(
                        f"  - {currency_code}: {balance:.2f} "
                        f"→ курс недоступен",
                        file=sys.stderr,
                    )
                    continue
                value_in_base = balance * rate

            total_value += value_in_base
            print(
                f"  - {currency_code}: {balance:.4f} "
                f"→ {value_in_base:.2f} {base}"
            )

        print("  ---------------------------------")
        print(f"  ИТОГО: {total_value:,.2f} {base}")

    def buy(self, currency: str, amount: float) -> None:
        """
        Купить валюту.

        Args:
            currency: Код покупаемой валюты
            amount: Количество валюты
        """
        self._require_login()

        currency = _validate_currency(currency)
        amount = self._validate_amount(amount)

        portfolio = self.portfolio_manager.get_portfolio(
            self.current_user.user_id
        )

        # Получаем старый баланс
        wallet = portfolio.get_wallet(currency)
        old_balance = wallet.balance if wallet else 0.0

        try:
            rate, cost_usd = self.portfolio_manager.buy_currency(
                self.current_user.user_id,
                currency,
                amount,
                self.rate_manager,
            )

            # Получаем новый баланс
            portfolio = self.portfolio_manager.get_portfolio(
                self.current_user.user_id
            )
            wallet = portfolio.get_wallet(currency)
            new_balance = wallet.balance if wallet else 0.0

            print(
                f"Покупка выполнена: {amount:.4f} {currency} "
                f"по курсу {rate:.2f} USD/{currency}"
            )
            print("Изменения в портфеле:")
            print(
                f"  - {currency}: было {old_balance:.4f} → "
                f"стало {new_balance:.4f}"
            )
            print(f"Оценочная стоимость покупки: {cost_usd:,.2f} USD")

        except InsufficientFundsError as e:
            # Показываем сообщение как есть
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except (CurrencyNotFoundError, RateUnavailableError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except ApiRequestError as e:
            print(
                f"{e}\nПовторите попытку позже или проверьте сеть.",
                file=sys.stderr,
            )
            sys.exit(1)
        except ValueError as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            sys.exit(1)

    def sell(self, currency: str, amount: float) -> None:
        """
        Продать валюту.

        Args:
            currency: Код продаваемой валюты
            amount: Количество валюты
        """
        self._require_login()

        currency = _validate_currency(currency)
        amount = self._validate_amount(amount)

        portfolio = self.portfolio_manager.get_portfolio(
            self.current_user.user_id
        )

        # Получаем старый баланс
        wallet = portfolio.get_wallet(currency)
        if wallet is None:
            print(
                f"У вас нет кошелька '{currency}'. "
                f"Добавьте валюту: она создаётся автоматически "
                f"при первой покупке.",
                file=sys.stderr,
            )
            sys.exit(1)

        old_balance = wallet.balance

        try:
            rate, revenue_usd = self.portfolio_manager.sell_currency(
                self.current_user.user_id,
                currency,
                amount,
                self.rate_manager,
            )

            # Получаем новый баланс
            portfolio = self.portfolio_manager.get_portfolio(
                self.current_user.user_id
            )
            wallet = portfolio.get_wallet(currency)
            new_balance = wallet.balance if wallet else 0.0

            print(
                f"Продажа выполнена: {amount:.4f} {currency} "
                f"по курсу {rate:.2f} USD/{currency}"
            )
            print("Изменения в портфеле:")
            print(
                f"  - {currency}: было {old_balance:.4f} → "
                f"стало {new_balance:.4f}"
            )
            print(f"Оценочная выручка: {revenue_usd:,.2f} USD")

        except InsufficientFundsError as e:
            # Показываем сообщение как есть
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except WalletNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except (CurrencyNotFoundError, RateUnavailableError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except ApiRequestError as e:
            print(
                f"{e}\nПовторите попытку позже или проверьте сеть.",
                file=sys.stderr,
            )
            sys.exit(1)
        except ValueError as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            sys.exit(1)

    def get_rate(self, from_currency: str, to_currency: str) -> None:
        """
        Получить курс валюты.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
        """
        try:
            from_currency = _validate_currency(from_currency)
            to_currency = _validate_currency(to_currency)
        except (ValueError, CurrencyNotFoundError) as e:
            print(str(e), file=sys.stderr)
            print(
                "\nПопробуйте: project get-rate --help "
                "или проверьте список поддерживаемых валют",
                file=sys.stderr,
            )
            # Показываем список доступных валют
            currencies = list_currencies()
            if currencies:
                print("\nДоступные валюты:", file=sys.stderr)
                for curr in sorted(currencies, key=lambda x: x.code)[:10]:
                    print(f"  - {curr.code}", file=sys.stderr)
            sys.exit(1)

        try:
            rate = self.rate_manager.get_or_fetch_rate(
                from_currency, to_currency
            )
        except CurrencyNotFoundError as e:
            print(str(e), file=sys.stderr)
            print(
                "\nПопробуйте: project get-rate --help "
                "или проверьте список поддерживаемых валют",
                file=sys.stderr,
            )
            sys.exit(1)
        except ApiRequestError as e:
            print(
                f"{e}\nПовторите попытку позже или проверьте сеть.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Получаем метку времени
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key not in self.rate_manager._rates:
            reverse_key = f"{to_currency}_{from_currency}"
            if reverse_key in self.rate_manager._rates:
                rate_key = reverse_key

        updated_at = "неизвестно"
        if rate_key in self.rate_manager._rates:
            updated_at_str = self.rate_manager._rates[rate_key].get(
                "updated_at"
            )
            if updated_at_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated_at_str)
                    updated_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    pass

        print(
            f"Курс {from_currency}→{to_currency}: {rate:.8f} "
            f"(обновлено: {updated_at})"
        )

        # Обратный курс
        if rate != 0:
            reverse_rate = 1.0 / rate
            print(f"Обратный курс {to_currency}→{from_currency}: "
                  f"{reverse_rate:.2f}")

    def update_rates(self, source: str | None = None) -> None:
        """
        Обновить курсы валют из внешних API.

        Args:
            source: Источник для обновления
                ('coingecko', 'exchangerate' или None для всех)
        """
        try:
            updater = RatesUpdater()
            result = updater.run_update(source)

            if result["errors"]:
                print(
                    "Update completed with errors. "
                    "Check logs/actions.log for details.",
                    file=sys.stderr,
                )
                for error in result["errors"]:
                    print(f"  - {error}", file=sys.stderr)
            else:
                print(
                    f"Update successful. "
                    f"Total rates updated: {result['total_rates']}. "
                    f"Last refresh: {result['last_refresh']}"
                )

        except ApiRequestError as e:
            print(
                f"{e}\nПовторите попытку позже или проверьте сеть.",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(
                f"Ошибка при обновлении курсов: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    def show_rates(
        self,
        currency: str | None = None,
        top: int | None = None,
        base: str | None = None,
    ) -> None:
        """
        Показать курсы валют из локального кеша.

        Args:
            currency: Показать курс только для указанной валюты
            top: Показать N самых дорогих криптовалют
            base: Базовая валюта для отображения
        """
        storage = RatesStorage()
        cache_data = storage.load_rates_cache()

        pairs = cache_data.get("pairs", {})
        last_refresh = cache_data.get("last_refresh")

        if not pairs:
            print(
                "Локальный кеш курсов пуст. "
                "Выполните 'update-rates', чтобы загрузить данные.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Фильтрация по валюте
        if currency:
            currency = _validate_currency(currency)
            filtered_pairs = {
                pair: data
                for pair, data in pairs.items()
                if pair.startswith(f"{currency}_")
                or pair.endswith(f"_{currency}")
            }

            if not filtered_pairs:
                print(
                    f"Курс для '{currency}' не найден в кеше.",
                    file=sys.stderr,
                )
                sys.exit(1)

            pairs = filtered_pairs

        # Фильтрация по топу (только для криптовалют)
        if top is not None and top > 0:
            # Выбираем только криптовалюты (BTC, ETH и т.д.)
            crypto_prefixes = (
                "BTC_", "ETH_", "SOL_", "LTC_", "XRP_", "ADA_", "DOT_"
            )
            crypto_pairs = {
                pair: data
                for pair, data in pairs.items()
                if pair.startswith(crypto_prefixes)
            }

            if crypto_pairs:
                # Сортируем по курсу (по убыванию)
                sorted_pairs = sorted(
                    crypto_pairs.items(),
                    key=lambda x: x[1].get("rate", 0),
                    reverse=True,
                )[:top]
                pairs = dict(sorted_pairs)

        # Форматирование вывода
        if last_refresh:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(
                    last_refresh.replace("Z", "+00:00")
                )
                refresh_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                refresh_str = last_refresh
        else:
            refresh_str = "неизвестно"

        print(f"Rates from cache (updated at {refresh_str}):")

        # Сортируем пары для вывода
        sorted_pairs = sorted(
            pairs.items(), key=lambda x: x[0]
        )

        for pair, data in sorted_pairs:
            rate = data.get("rate", 0)
            source = data.get("source", "Unknown")
            source_str = f" (source: {source})" if source != "Unknown" else ""
            print(f"  - {pair}: {rate:.2f}{source_str}")


def main() -> None:
    """Точка входа в CLI."""
    parser = argparse.ArgumentParser(
        description="ValutaTrade Hub - управление валютным кошельком"
    )
    subparsers = parser.add_subparsers(dest="command", help="Команды")

    # Команда register
    register_parser = subparsers.add_parser(
        "register", help="Зарегистрировать нового пользователя"
    )
    register_parser.add_argument(
        "--username", required=True, help="Имя пользователя"
    )
    register_parser.add_argument(
        "--password", required=True, help="Пароль (минимум 4 символа)"
    )

    # Команда login
    login_parser = subparsers.add_parser("login", help="Войти в систему")
    login_parser.add_argument(
        "--username", required=True, help="Имя пользователя"
    )
    login_parser.add_argument(
        "--password", required=True, help="Пароль"
    )

    # Команда show-portfolio
    portfolio_parser = subparsers.add_parser(
        "show-portfolio", help="Показать портфель"
    )
    portfolio_parser.add_argument(
        "--base",
        default="USD",
        help="Базовая валюта (по умолчанию USD)",
    )

    # Команда buy
    buy_parser = subparsers.add_parser("buy", help="Купить валюту")
    buy_parser.add_argument(
        "--currency", required=True, help="Код покупаемой валюты"
    )
    buy_parser.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Количество покупаемой валюты",
    )

    # Команда sell
    sell_parser = subparsers.add_parser("sell", help="Продать валюту")
    sell_parser.add_argument(
        "--currency", required=True, help="Код продаваемой валюты"
    )
    sell_parser.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Количество продаваемой валюты",
    )

    # Команда get-rate
    rate_parser = subparsers.add_parser("get-rate", help="Получить курс")
    rate_parser.add_argument(
        "--from", dest="from_currency", required=True, help="Исходная валюта"
    )
    rate_parser.add_argument(
        "--to", dest="to_currency", required=True, help="Целевая валюта"
    )

    # Команда update-rates
    update_rates_parser = subparsers.add_parser(
        "update-rates", help="Обновить курсы валют из внешних API"
    )
    update_rates_parser.add_argument(
        "--source",
        choices=["coingecko", "exchangerate"],
        help="Обновить данные только из указанного источника",
    )

    # Команда show-rates
    show_rates_parser = subparsers.add_parser(
        "show-rates", help="Показать курсы валют из локального кеша"
    )
    show_rates_parser.add_argument(
        "--currency", help="Показать курс только для указанной валюты"
    )
    show_rates_parser.add_argument(
        "--top",
        type=int,
        help="Показать N самых дорогих криптовалют",
    )
    show_rates_parser.add_argument(
        "--base",
        help="Базовая валюта для отображения (пока не используется)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    interface = CLIInterface()

    if args.command == "register":
        interface.register(args.username, args.password)
    elif args.command == "login":
        interface.login(args.username, args.password)
    elif args.command == "show-portfolio":
        interface.show_portfolio(args.base)
    elif args.command == "buy":
        interface.buy(args.currency, args.amount)
    elif args.command == "sell":
        interface.sell(args.currency, args.amount)
    elif args.command == "get-rate":
        interface.get_rate(args.from_currency, args.to_currency)
    elif args.command == "update-rates":
        interface.update_rates(args.source)
    elif args.command == "show-rates":
        interface.show_rates(
            currency=args.currency,
            top=args.top,
            base=args.base,
        )


if __name__ == "__main__":
    main()
