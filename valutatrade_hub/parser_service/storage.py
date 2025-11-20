"""Хранилище для курсов валют."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.parser_service.config import config


class RatesStorage:
    """Хранилище для работы с файлами курсов валют."""

    def __init__(
        self,
        rates_file: Path | None = None,
        history_file: Path | None = None,
    ) -> None:
        """
        Инициализация хранилища.

        Args:
            rates_file: Путь к файлу rates.json
            history_file: Путь к файлу exchange_rates.json
        """
        self.rates_file = rates_file or config.rates_file_path
        self.history_file = history_file or config.history_file_path

        # Создаём директории, если их нет
        self.rates_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def _write_atomic(
        self, file_path: Path, data: dict[str, Any]
    ) -> None:
        """
        Атомарная запись JSON файла.

        Args:
            file_path: Путь к файлу
            data: Данные для записи
        """
        # Создаём временный файл
        temp_file = file_path.with_suffix(".tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Атомарно переименовываем
            temp_file.replace(file_path)
        except Exception:
            # Удаляем временный файл при ошибке
            if temp_file.exists():
                temp_file.unlink()
            raise

    def save_rate_to_history(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        source: str,
        meta: dict[str, Any] | None = None,
    ) -> str:
        """
        Сохранить курс в исторический журнал (exchange_rates.json).

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            rate: Курс обмена
            source: Источник курса
            meta: Метаданные (request_ms, status_code и т.д.)

        Returns:
            ID записи
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        record_id = f"{from_currency}_{to_currency}_{timestamp}"

        record = {
            "id": record_id,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "rate": rate,
            "timestamp": timestamp,
            "source": source,
            "meta": meta or {},
        }

        # Загружаем существующую историю
        history = self.load_history()

        # Добавляем новую запись
        if "records" not in history:
            history["records"] = []

        history["records"].append(record)

        # Сохраняем
        self._write_atomic(self.history_file, history)

        return record_id

    def save_rates_cache(
        self,
        rates: dict[str, float],
        sources: dict[str, str],
    ) -> None:
        """
        Сохранить кеш курсов в rates.json.

        Args:
            rates: Словарь курсов {pair: rate}
            sources: Словарь источников {pair: source}
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        pairs_data: dict[str, dict[str, Any]] = {}

        for pair, rate in rates.items():
            parts = pair.split("_")
            if len(parts) != 2:
                continue

            from_curr, to_curr = parts
            source = sources.get(pair, "Unknown")

            pairs_data[pair] = {
                "rate": rate,
                "updated_at": timestamp,
                "source": source,
            }

        cache_data = {
            "pairs": pairs_data,
            "last_refresh": timestamp,
        }

        # Сохраняем атомарно
        self._write_atomic(self.rates_file, cache_data)

    def load_history(self) -> dict[str, Any]:
        """
        Загрузить исторический журнал.

        Returns:
            Словарь с историей курсов
        """
        if not self.history_file.exists():
            return {"records": []}

        try:
            with open(self.history_file, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"records": []}

    def load_rates_cache(self) -> dict[str, Any]:
        """
        Загрузить кеш курсов.

        Returns:
            Словарь с кешем курсов
        """
        if not self.rates_file.exists():
            return {"pairs": {}, "last_refresh": None}

        try:
            with open(self.rates_file, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"pairs": {}, "last_refresh": None}

