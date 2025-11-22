"""Клиенты для работы с внешними API."""

from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import config


class BaseApiClient(ABC):
    """Абстрактный базовый класс для API клиентов."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """
        Получить курсы валют от API.

        Returns:
            Словарь в формате {currency_pair: rate}
            (например, {"BTC_USD": 59337.21})

        Raises:
            ApiRequestError: Если запрос не удался
        """
        pass

    def _make_request(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Выполнить HTTP запрос с обработкой ошибок.

        Args:
            url: URL для запроса
            params: Параметры запроса

        Returns:
            JSON ответ от API

        Raises:
            ApiRequestError: Если запрос не удался
        """
        try:
            response = requests.get(
                url,
                params=params,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            raise ApiRequestError(
                f"Таймаут при обращении к API: {url}"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise ApiRequestError(
                f"Ошибка подключения к API: {url}"
            ) from e
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            if status_code == 429:
                raise ApiRequestError(
                    f"Превышен лимит запросов к API: {url}"
                ) from e
            raise ApiRequestError(
                f"HTTP ошибка {status_code} при обращении к API: {url}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(
                f"Ошибка при обращении к API: {url}: {str(e)}"
            ) from e
        except ValueError as e:
            raise ApiRequestError(
                f"Некорректный JSON ответ от API: {url}"
            ) from e


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API."""

    def fetch_rates(self) -> dict[str, float]:
        """
        Получить курсы криптовалют от CoinGecko.

        Returns:
            Словарь в формате {CRYPTO_USD: rate}

        Raises:
            ApiRequestError: Если запрос не удался
        """
        # Формируем список ID криптовалют
        crypto_ids = [
            config.CRYPTO_ID_MAP.get(code, code.lower())
            for code in config.CRYPTO_CURRENCIES
            if code in config.CRYPTO_ID_MAP
        ]

        if not crypto_ids:
            return {}

        # Формируем параметры запроса
        params = {
            "ids": ",".join(crypto_ids),
            "vs_currencies": config.BASE_CURRENCY.lower(),
        }

        # Выполняем запрос
        response_data = self._make_request(
            config.COINGECKO_URL, params=params
        )

        # Преобразуем ответ в стандартный формат
        rates: dict[str, float] = {}

        for crypto_code in config.CRYPTO_CURRENCIES:
            crypto_id = config.CRYPTO_ID_MAP.get(crypto_code)
            if not crypto_id or crypto_id not in response_data:
                continue

            crypto_data = response_data[crypto_id]
            base_lower = config.BASE_CURRENCY.lower()

            if base_lower in crypto_data:
                pair_key = f"{crypto_code}_{config.BASE_CURRENCY}"
                rates[pair_key] = float(crypto_data[base_lower])

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API."""

    def __init__(self, api_key: str | None = None) -> None:
        """
        Инициализация клиента.

        Args:
            api_key: API ключ (если None, используется из config)
        """
        self.api_key = api_key or config.EXCHANGERATE_API_KEY

        if not self.api_key:
            raise ValueError(
                "ExchangeRate API ключ не установлен. "
                "Установите EXCHANGERATE_API_KEY в переменных окружения."
            )

    def fetch_rates(self) -> dict[str, float]:
        """
        Получить курсы фиатных валют от ExchangeRate-API.

        Returns:
            Словарь в формате {FIAT_USD: rate}

        Raises:
            ApiRequestError: Если запрос не удался
        """
        # Формируем URL
        url = (
            f"{config.EXCHANGERATE_API_URL}/"
            f"{self.api_key}/latest/{config.BASE_CURRENCY}"
        )

        # Выполняем запрос
        response_data = self._make_request(url)

        # Проверяем результат
        result = response_data.get("result")
        if result != "success":
            error_type = response_data.get("error-type", "unknown")
            error_info = response_data.get("error-info", "")
            raise ApiRequestError(
                f"ExchangeRate-API вернул ошибку: {error_type}. "
                f"{error_info if error_info else 'Проверьте API ключ.'}"
            )

        # Извлекаем курсы
        # ExchangeRate-API v6 использует 'conversion_rates', старые версии - 'rates'
        rates_data = response_data.get("conversion_rates") or response_data.get("rates", {})

        if not rates_data:
            # Проверяем структуру ответа для отладки
            from valutatrade_hub.logging_config import get_logger
            logger = get_logger(__name__)
            response_keys = list(response_data.keys())
            logger.error(
                f"ExchangeRate-API вернул пустой rates. "
                f"Response keys: {response_keys}, "
                f"Response data: {response_data}"
            )
            raise ApiRequestError(
                f"ExchangeRate-API вернул пустой список курсов. "
                f"Ответ содержит ключи: {response_keys}. "
                f"Проверьте API ключ и тарифный план."
            )

        # Преобразуем в стандартный формат
        rates: dict[str, float] = {}

        for fiat_code in config.FIAT_CURRENCIES:
            if fiat_code == config.BASE_CURRENCY:
                continue  # Пропускаем базовую валюту

            if fiat_code in rates_data:
                pair_key = f"{fiat_code}_{config.BASE_CURRENCY}"
                rates[pair_key] = float(rates_data[fiat_code])

        # Если не нашли ни одного курса из списка, но rates_data не пустой,
        # пробуем взять популярные валюты
        if not rates and rates_data:
            from valutatrade_hub.logging_config import get_logger
            logger = get_logger(__name__)
            available_currencies = list(rates_data.keys())[:10]
            logger.warning(
                f"Не найдено валют из FIAT_CURRENCIES в ответе API. "
                f"Доступные валюты (первые 10): {available_currencies}"
            )
            # Пробуем взять хотя бы несколько популярных валют
            common_currencies = ["EUR", "GBP", "RUB", "JPY", "CHF", "CNY", "CAD", "AUD"]
            for curr in common_currencies:
                if curr in rates_data and curr != config.BASE_CURRENCY:
                    pair_key = f"{curr}_{config.BASE_CURRENCY}"
                    rates[pair_key] = float(rates_data[curr])
                    logger.info(
                        f"Добавлен курс {pair_key} = {rates[pair_key]} "
                        f"(не в списке FIAT_CURRENCIES)"
                    )

        # Если rates всё ещё пустой, значит проблема серьёзная
        if not rates:
            from valutatrade_hub.logging_config import get_logger
            logger = get_logger(__name__)
            logger.error(
                f"Не удалось извлечь ни одного курса. "
                f"rates_data содержит {len(rates_data)} записей, "
                f"но ни одна не подошла."
            )

        return rates

