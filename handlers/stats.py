from aiogram import Router, types
from aiogram.filters import Command

router = Router()


"""
Обработчик команд статистики
"""


@router.message(Command("today"))
async def cmd_today(message: types.Message):
    """Статистика за сегодня"""
    await message.answer("📊 Статистика за сегодня:\n"
                       "⏱️ Работа: 0ч 0мин\n"
                       "⏸️ Перерывы: 0мин\n"
                       "📈 Продуктивность: 0%")

@router.message(Command("week"))
async def cmd_week(message: types.Message):
    """Статистика за неделю"""
    await message.answer("📅 Статистика за неделю:\n"
                       "📊 Среднее время работы: 0ч 0мин\n"
                       "📈 Самый продуктивный день: Понедельник")