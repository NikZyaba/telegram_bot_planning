from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    """Основное меню бота"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="▶️ Начать день", callback_data="start_work"),
            InlineKeyboardButton(text="⏸️ Пауза", callback_data="pause")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats_menu"),
            InlineKeyboardButton(text="⏹️ Завершить день", callback_data="stop_work")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ]
    ])
    return keyboard

def get_stats_menu():
    """Меню статистики"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data="stats_today"),
            InlineKeyboardButton(text="📅 Неделя", callback_data="stats_week")
        ],
        [
            InlineKeyboardButton(text="📈 Месяц", callback_data="stats_month"),
            InlineKeyboardButton(text="📊 Все время", callback_data="stats_all")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_manu")
        ]
    ])
    return keyboard