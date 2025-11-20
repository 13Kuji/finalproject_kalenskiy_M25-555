"""Конфигурация логирования приложения.

Используется строковый формат для читабельности.
Поддерживается ротация файлов по размеру.
"""

import logging
import logging.handlers
from pathlib import Path

from valutatrade_hub.infra.settings import settings


def setup_logging(
    level: str | None = None,
    log_file: Path | None = None,
    format_string: str | None = None,
) -> None:
    """
    Настроить логирование приложения.

    Args:
        level: Уровень логирования (по умолчанию из settings)
        log_file: Путь к файлу логов (по умолчанию из settings)
        format_string: Формат логов (не используется,
            оставлен для совместимости)
    """
    log_level = level or settings.log_level
    log_file_path = log_file or settings.log_file

    # Создаём директорию для логов
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Форматтер для файла (ISO timestamp)
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Обработчик для файла с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(file_formatter)

    # Обработчик для консоли (только WARNING и выше)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        "%(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # Удаляем существующие обработчики
    root_logger.handlers.clear()

    # Добавляем новые обработчики
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с указанным именем.

    Args:
        name: Имя логгера (обычно __name__)

    Returns:
        Объект Logger
    """
    return logging.getLogger(name)

