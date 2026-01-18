from aiogram import Router, types
from aiogram.filters import Command

from database import get_db, add_user

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
        await message.answer(welcome_text)
    except Exception as e:
        await message.answer("⚠️ Произошла ошибка. Попробуйте еще раз.")
    finally:
        # Закрываем сессию в БД
        next(db_get, None)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды help/"""
    await message.answer(
        "Ты меня просишь о помощи, уже?\n"
        "М-да ИИ точно скоро заменит людишек. Шутка!\n\n"
        "ℹ️ Помощь по использованию бота:\n\n"
        "1. Начните день: /start_work\n"
        "2. Закончите день: /stop_work\n"
        "3. Для перерыва: /pause\n"
        "4. Посмотреть статистику: /today или /week\n\n"
        "📊 Бот автоматически учитывает паузы и рабочее время."
    )