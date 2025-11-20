"""Точка входа в приложение ValutaTrade Hub."""

from valutatrade_hub.cli.interface import main
from valutatrade_hub.logging_config import setup_logging

# Настраиваем логирование при запуске приложения
setup_logging()

if __name__ == "__main__":
    main()

