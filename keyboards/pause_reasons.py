from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

"""Клавиатура выбора паузы"""

def get_pause_reasons_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="☕ Кофе-брейк", callback_data="pause_reason:coffee"),
            InlineKeyboardButton(text="🍽️ Обед", callback_data="pause_reason:lunch")
        ],
        [
            InlineKeyboardButton(text="📞 Звонок/встреча", callback_data="pause_reason:call"),
            InlineKeyboardButton(text="💻 Технический перерыв", callback_data="pause_reason:technical")
        ],
        [
            InlineKeyboardButton(text="🚬 Перекур", callback_data="pause_reason:smoke"),
            InlineKeyboardButton(text="🚶 Отлучился", callback_data="pause_reason:away")
        ],
        [
            InlineKeyboardButton(text="🎯 Без причины", callback_data="pause_reason:none"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="pause_cancel")
        ]
    ])
    return keyboard

def get_pause_actions_keyboard():
    """Клавиатура действий с паузой"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏸️ Завершить перерыв", callback_data="pause_stop"),
            InlineKeyboardButton(text="ℹ️ Инфо о паузе", callback_data="pause_info")
        ],
        [
            InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")
        ]
    ])
    return keyboard