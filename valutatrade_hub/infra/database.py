"""Абстракция над JSON-хранилищем (Singleton)."""

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import settings


class DatabaseManager:
    """Singleton для управления JSON-хранилищем данных."""

    _instance: "DatabaseManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        """Создать единственный экземпляр DatabaseManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализация менеджера базы данных (только один раз)."""
        if self._initialized:
            return

        self.data_dir = Path(settings.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def load(self, table_name: str) -> Any:
        """
        Загрузить данные из таблицы (JSON файла).

        Args:
            table_name: Имя таблицы (имя файла без расширения)

        Returns:
            Загруженные данные (dict или list)

        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: Если файл содержит некорректный JSON
        """
        file_path = self.data_dir / f"{table_name}.json"

        if not file_path.exists():
            # Возвращаем значение по умолчанию
            if table_name == "rates":
                return {}
            return []

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, table_name: str, data: Any) -> None:
        """
        Сохранить данные в таблицу (JSON файл).

        Args:
            table_name: Имя таблицы (имя файла без расширения)
            data: Данные для сохранения

        Raises:
            json.JSONEncodeError: Если данные не могут быть сериализованы
        """
        file_path = self.data_dir / f"{table_name}.json"

        # Создаём директорию, если её нет
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def table_exists(self, table_name: str) -> bool:
        """
        Проверить существование таблицы.

        Args:
            table_name: Имя таблицы

        Returns:
            True если таблица существует, False иначе
        """
        file_path = self.data_dir / f"{table_name}.json"
        return file_path.exists()


# Глобальный экземпляр менеджера БД
db = DatabaseManager()

