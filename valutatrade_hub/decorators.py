"""Декораторы для расширения функциональности."""

import functools
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from valutatrade_hub.logging_config import get_logger

logger = get_logger(__name__)


def log_action(
    action_name: str | None = None,
    verbose: bool = False,
):
    """
    Декоратор для логирования доменных операций.

    Логирует на уровне INFO следующую структуру:
    - timestamp (ISO)
    - action (BUY/SELL/REGISTER/LOGIN и т.д.)
    - username (или user_id)
    - currency_code, amount
    - rate и base (если применимо)
    - result (OK/ERROR)
    - error_type/error_message при исключениях

    Args:
        action_name: Имя действия для логов
            (если None, используется имя функции)
        verbose: Если True, добавляет дополнительный контекст
            (например, состояние кошелька «было→стало»)

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            action = action_name or func.__name__.upper()

            # Извлекаем параметры из args/kwargs
            user_id = None
            username = "anonymous"
            currency_code = None
            amount = None
            rate = None
            base = "USD"

            # Для методов usecases: первый арг - self, второй - user_id
            if len(args) > 1:
                user_id = args[1] if isinstance(args[1], int) else None
                if len(args) > 2:
                    currency_code = (
                        args[2]
                        if isinstance(args[2], str)
                        else kwargs.get("currency")
                    )
                if len(args) > 3:
                    amount = (
                        args[3]
                        if isinstance(args[3], int | float)
                        else kwargs.get("amount")
                    )

            # Извлекаем из kwargs
            currency_code = (
                currency_code
                or kwargs.get("currency")
                or kwargs.get("currency_code")
            )
            amount = amount or kwargs.get("amount")
            rate = kwargs.get("rate")
            base = kwargs.get("base", "USD")

            # Для CLI методов: ищем current_user
            if args and hasattr(args[0], "current_user"):
                user = args[0].current_user
                if user is not None:
                    username = user.username
                    user_id = user.user_id

            # Формируем базовое сообщение
            timestamp = datetime.now().isoformat()
            log_parts = [
                f"{timestamp}",
                f"action={action}",
                f"user='{username}'",
            ]

            if user_id:
                log_parts.append(f"user_id={user_id}")

            if currency_code:
                log_parts.append(f"currency='{currency_code}'")

            if amount is not None:
                log_parts.append(f"amount={amount:.4f}")

            if rate is not None:
                log_parts.append(f"rate={rate:.2f}")

            if base:
                log_parts.append(f"base='{base}'")

            # Сохраняем состояние для verbose режима
            old_state = None

            try:
                # Для buy/sell сохраняем старое состояние кошелька
                if verbose and action in ("BUY", "SELL") and currency_code:
                    if args and hasattr(args[0], "get_portfolio"):
                        portfolio = args[0].get_portfolio(user_id)
                        wallet = portfolio.get_wallet(currency_code)
                        if wallet:
                            old_state = wallet.balance

                result = func(*args, **kwargs)

                # Извлекаем rate и стоимость из результата (для buy/sell)
                if isinstance(result, tuple) and len(result) == 2:
                    result_rate, cost_or_revenue = result
                    rate = result_rate
                    log_parts = [
                        p for p in log_parts if not p.startswith("rate=")
                    ]
                    log_parts.append(f"rate={rate:.2f}")
                    if action == "BUY":
                        log_parts.append(
                            f"cost_usd={cost_or_revenue:.2f}"
                        )
                    elif action == "SELL":
                        log_parts.append(
                            f"revenue_usd={cost_or_revenue:.2f}"
                        )

                # Добавляем verbose информацию
                if verbose and old_state is not None:
                    if args and hasattr(args[0], "get_portfolio"):
                        portfolio = args[0].get_portfolio(user_id)
                        wallet = portfolio.get_wallet(currency_code)
                        if wallet:
                            new_state = wallet.balance
                            log_parts.append(
                                f"balance_before={old_state:.4f}"
                            )
                            log_parts.append(
                                f"balance_after={new_state:.4f}"
                            )

                log_parts.append("result=OK")
                logger.info(" ".join(log_parts))

                return result

            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)

                log_parts.append("result=ERROR")
                log_parts.append(f"error_type={error_type}")
                log_parts.append(f"error_message='{error_message}'")

                logger.error(" ".join(log_parts), exc_info=True)

                # Декоратор НЕ глотает исключения - пробрасывает дальше
                raise

        return wrapper

    return decorator


def measure_time(func: Callable) -> Callable:
    """
    Декоратор для измерения времени выполнения функции.

    Returns:
        Декорированная функция
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_time = time.time() - start_time
            logger.debug(
                f"Function {func.__name__} executed in "
                f"{elapsed_time:.4f} seconds"
            )

    return wrapper


def confirm_action(message: str = "Вы уверены?"):
    """
    Декоратор для подтверждения действия пользователем.

    Args:
        message: Сообщение для подтверждения

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            response = input(f"{message} (yes/no): ").strip().lower()
            if response not in ("yes", "y"):
                logger.info(
                    f"Action {func.__name__} cancelled by user"
                )
                return None

            return func(*args, **kwargs)

        return wrapper

    return decorator

