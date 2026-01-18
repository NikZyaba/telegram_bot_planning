import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import init_db

"""
Основной файл для запуска Telegram бота.
Точка входа в приложение.
"""

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Основная асинхронная функция запуска бота"""

    logger.info("=" * 50)
    logger.info("Запуск бота учета рабочего времени")
    logger.info("=" * 50)

    # 1. Инициализация базы данных
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return

    # 2. Создание экземпляра бота с настройками
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 3. Создание диспетчера с хранилищем состояний
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 4. Регистрация middleware (будет позже)


    # 5. Регистрация роутеров (handlers)
    # Сначала импортируем их
    try:
        from handlers.start import router as start_router
        from handlers.time_tracking import router as time_router
        from handlers.stats import router as stats_router

        dp.include_router(start_router)
        dp.include_router(time_router)
        dp.include_router(stats_router)

        logger.info("✅ Роутеры зарегистрированы")
    except ImportError as e:
        logger.warning(f"⚠️ Некоторые handlers не найдены: {e}")
        logger.warning("Создайте базовые handlers для продолжения")

    # 6. Команды бота (отобразятся в интерфейсе Telegram)
    commands = [
        {"command": "start", "description": "Запустить бота"},
        {"command": "help", "description": "Помощь"},
        {"command": "start_work", "description": "Начать рабочий день"},
        {"command": "stop_work", "description": "Закончить рабочий день"},
        {"command": "pause", "description": "Начать/закончить перерыв"},
        {"command": "today", "description": "Статистика за сегодня"},
        {"command": "week", "description": "Статистика за неделю"},
    ]

    try:
        await bot.set_my_commands(commands)
        logger.info("✅ Команды бота установлены")
    except Exception as e:
        logger.error(f"❌ Ошибка установки команд: {e}")

    # 7. Уведомление админам о запуске
    if config.bot.admin_ids:
        for admin_id in config.bot.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    "🤖 Бот учета рабочего времени запущен!\n"
                    f"⏰ Время: {config.time.timezone}"
                )
                logger.info(f"✅ Уведомление отправлено админу {admin_id}")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")

    # 8. Запуск поллинга (опрос сервера Telegram)
    logger.info("✅ Бот запущен и ожидает сообщений...")
    logger.info("=" * 50)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        # Корректное завершение
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    # Запуск асинхронной главной функции
    asyncio.run(main())
