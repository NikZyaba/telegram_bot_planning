from aiogram import Router, types
from aiogram.filters import Command

from database import get_db, add_user
from keyboards.main_menu import get_main_menu

"""
Обработчик команд /start и /help
"""


router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды start/"""
    """Регистрируем пользователя (подготовка к сохранению в БД)"""
    user = message.from_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    # Получаем сессию БД
    db_get = get_db()
    db = next(db_get)
    try:
        db_user = add_user(
            db=db,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        # Приветствуем пользователя
        welcome_text = (
            f"👋 Привет, {first_name or 'друг'}!\n"
            f"🆔 Твой ID: {telegram_id}\n\n"
            "📋 Я бот для учета рабочего времени.\n\n"
            "⚡ Доступные команды:\n"
            "/start_work - начать рабочий день\n"
            "/stop_work - закончить рабочий день\n"
            "/pause - начать/закончить перерыв\n"
            "/today - статистика за сегодня\n"
            "/week - статистика за неделю\n"
            "/help - помощь\n\n"
            "💡 Начните с команды /start_work"
        )
        await message.answer(welcome_text, reply_markup=get_main_menu())
    except Exception as e:
        await message.answer("⚠️ Произошла ошибка. Попробуйте еще раз.")
        print(f"Ошибка при старте {e}")
    finally:
        # Закрываем сессию в БД
        next(db_get, None)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды help/"""
    help_text = (
        "ℹ️ **Помощь по использованию бота:**\n\n"
        "🎯 **Основные команды:**\n"
        "• /start_work - начать рабочий день\n"
        "• /stop_work - закончить рабочий день\n"
        "• /pause - начать/закончить перерыв\n"
        "• /today - статистика за сегодня\n"
        "• /week - статистика за неделю\n\n"

        "📱 **Использование меню:**\n"
        "Используйте кнопки меню для быстрого доступа к функциям\n\n"

        "⏰ **Рекомендации:**\n"
        "1. Начинайте день командой /start_work\n"
        "2. Делайте перерывы каждые 1.5-2 часа\n"
        "3. Завершайте день командой /stop_work\n"
        "4. Смотрите статистику для анализа продуктивности\n\n"

        "📞 **Поддержка:**\n"
        "Если возникли проблемы, напишите разработчику"
    )
    await message.answer(help_text)

# Команда для показа меню
@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Показать главное меню"""
    await message.answer(
        "🤖 **Главное меню**\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )