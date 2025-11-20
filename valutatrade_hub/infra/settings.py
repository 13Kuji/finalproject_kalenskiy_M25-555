"""Настройки приложения (Singleton).

Реализация через __new__ выбрана для простоты и читабельности.
Это стандартный паттерн для Python, не требует метаклассов
и легко понимается. Гарантирует единственный экземпляр
даже при множественных импортах.
"""

from pathlib import Path
from typing import Any


class SettingsLoader:
    """Singleton для загрузки и управления настройками приложения.

    Гарантирует единственный экземпляр в приложении.
    Используется для централизованного доступа к конфигурации.
    """

    _instance: "SettingsLoader | None" = None
    _initialized: bool = False

    def __new__(cls) -> "SettingsLoader":
        """Создать единственный экземпляр SettingsLoader.

        Returns:
            Единственный экземпляр SettingsLoader
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализация настроек (только один раз)."""
        if self._initialized:
            return

        # Путь к корню проекта
        self.project_root = Path(__file__).parent.parent.parent

        # Пути к данным
        self.data_dir = self.project_root / "data"
        self.session_file = self.project_root / ".session.json"

        # Настройки курсов валют
        self.rates_ttl_seconds = 300  # 5 минут в секундах
        self.rate_cache_max_age_minutes = 5  # Для обратной совместимости

        # Дефолтная базовая валюта
        self.default_base_currency = "USD"

        # Настройки логирования
        self.log_level = "INFO"  # INFO, DEBUG, WARNING, ERROR
        self.log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.log_file = self.project_root / "logs" / "actions.log"
        self.log_max_bytes = 10 * 1024 * 1024  # 10 MB
        self.log_backup_count = 5

        # Настройки API (для будущего использования)
        self.api_timeout_seconds = 30
        self.api_retry_attempts = 3

        # Создаём необходимые директории
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение настройки.

        Args:
            key: Ключ настройки
            default: Значение по умолчанию

        Returns:
            Значение настройки или default
        """
        return getattr(self, key, default)

    def reload(self) -> None:
        """Перезагрузить настройки.

        Сбрасывает флаг инициализации и повторно инициализирует
        все настройки. Полезно при изменении конфигурации
        во время выполнения.
        """
        self._initialized = False
        self.__init__()


# Глобальный экземпляр настроек
# Импорт этого объекта гарантирует использование единственного экземпляра
settings = SettingsLoader()

