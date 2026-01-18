import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    url: str = os.getenv("DATABASE_URL", "sqlite:///worktime.db")
    echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"


@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str = os.getenv("BOT_TOKEN")
    admin_ids: List[int] = field(default_factory=list)

    def __post_init__(self):
        """Парсим список ID админов из строки"""
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",")]


@dataclass
class TimeConfig:
    """Конфигурация времени"""
    timezone: str = os.getenv("TIMEZONE", "Europe/Minsk")
    workday_start_hour: int = int(os.getenv("WORKDAY_START_HOUR", "9"))
    workday_end_hour: int = int(os.getenv("WORKDAY_END_HOUR", "18"))
    notification_interval: int = int(os.getenv("NOTIFICATION_INTERVAL", "60"))


@dataclass
class Config:
    """Основной класс конфигурации"""
    bot: BotConfig = field(default_factory=BotConfig)
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    time: TimeConfig = field(default_factory=TimeConfig)


def load_config() -> Config:
    """Функция для загрузки конфигурации"""
    return Config()


# Глобальный объект конфигурации
config = load_config()


def validate_config():
    """Проверка обязательных переменных окружения"""
    required_vars = ["BOT_TOKEN"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}\n"
            "Создайте файл .env"
        )

    if not config.bot.token:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")


# Автоматическая валидация при импорте
try:
    validate_config()
except ValueError as e:
    print(f"Внимание: {e}")
