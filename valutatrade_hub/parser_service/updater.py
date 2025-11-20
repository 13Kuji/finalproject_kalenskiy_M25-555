"""Основной модуль обновления курсов валют."""

import time
from typing import Any

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage

logger = get_logger(__name__)


class RatesUpdater:
    """Класс для координации обновления курсов валют."""

    def __init__(
        self,
        storage: RatesStorage | None = None,
        crypto_client: BaseApiClient | None = None,
        fiat_client: BaseApiClient | None = None,
    ) -> None:
        """
        Инициализация обновлятеля курсов.

        Args:
            storage: Хранилище для сохранения курсов
            crypto_client: Клиент для криптовалют (CoinGecko)
            fiat_client: Клиент для фиатных валют (ExchangeRate-API)
        """
        self.storage = storage or RatesStorage()
        self.crypto_client = crypto_client or CoinGeckoClient()
        self.fiat_client = fiat_client

        # Создаём клиент фиатных валют только если есть ключ
        if self.fiat_client is None:
            try:
                self.fiat_client = ExchangeRateApiClient()
            except ValueError:
                logger.warning(
                    "ExchangeRate-API ключ не установлен. "
                    "Фиатные валюты не будут обновляться."
                )

    def run_update(self, source: str | None = None) -> dict[str, Any]:
        """
        Запустить обновление курсов валют.

        Args:
            source: Источник для обновления ('coingecko', 'exchangerate'
                или None для всех)

        Returns:
            Словарь с результатами обновления

        Raises:
            ApiRequestError: Если все клиенты не смогли получить данные
        """
        logger.info("Starting rates update...")

        all_rates: dict[str, float] = {}
        all_sources: dict[str, str] = {}
        errors: list[str] = []

        # Обновляем криптовалюты
        if source is None or source.lower() == "coingecko":
            try:
                logger.info("Fetching from CoinGecko...")
                start_time = time.time()

                crypto_rates = self.crypto_client.fetch_rates()

                elapsed_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    f"Fetching from CoinGecko... OK "
                    f"({len(crypto_rates)} rates)"
                )

                # Сохраняем в историю
                for pair, rate in crypto_rates.items():
                    parts = pair.split("_")
                    if len(parts) == 2:
                        from_curr, to_curr = parts
                        self.storage.save_rate_to_history(
                            from_curr,
                            to_curr,
                            rate,
                            "CoinGecko",
                            meta={
                                "request_ms": elapsed_ms,
                                "status_code": 200,
                            },
                        )

                all_rates.update(crypto_rates)
                all_sources.update(
                    {pair: "CoinGecko" for pair in crypto_rates.keys()}
                )

            except Exception as e:
                error_msg = f"Failed to fetch from CoinGecko: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        # Обновляем фиатные валюты
        if source is None or source.lower() == "exchangerate":
            if self.fiat_client is None:
                logger.warning(
                    "ExchangeRate-API клиент недоступен. "
                    "Пропускаем обновление фиатных валют."
                )
            else:
                try:
                    logger.info("Fetching from ExchangeRate-API...")
                    start_time = time.time()

                    fiat_rates = self.fiat_client.fetch_rates()

                    elapsed_ms = int((time.time() - start_time) * 1000)

                    logger.info(
                        f"Fetching from ExchangeRate-API... OK "
                        f"({len(fiat_rates)} rates)"
                    )

                    # Сохраняем в историю
                    for pair, rate in fiat_rates.items():
                        parts = pair.split("_")
                        if len(parts) == 2:
                            from_curr, to_curr = parts
                            self.storage.save_rate_to_history(
                                from_curr,
                                to_curr,
                                rate,
                                "ExchangeRate-API",
                                meta={
                                    "request_ms": elapsed_ms,
                                    "status_code": 200,
                                },
                            )

                    all_rates.update(fiat_rates)
                    all_sources.update(
                        {
                            pair: "ExchangeRate-API"
                            for pair in fiat_rates.keys()
                        }
                    )  # noqa: E501

                except Exception as e:
                    error_msg = (
                        f"Failed to fetch from ExchangeRate-API: {str(e)}"
                    )
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

        # Если нет ни одного курса, выбрасываем исключение
        if not all_rates:
            raise Exception(
                "Не удалось получить курсы ни от одного источника. "
                f"Ошибки: {'; '.join(errors)}"
            )

        # Сохраняем кеш
        rates_file_str = str(self.storage.rates_file)
        logger.info(
            f"Writing {len(all_rates)} rates to {rates_file_str}..."
        )
        self.storage.save_rates_cache(all_rates, all_sources)

        logger.info("Update successful.")

        result = {
            "total_rates": len(all_rates),
            "last_refresh": self.storage.load_rates_cache().get(
                "last_refresh"
            ),
            "errors": errors if errors else None,
        }

        return result

