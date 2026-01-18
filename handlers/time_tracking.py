from datetime import datetime
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from database import (
    get_db, get_user_by_telegram_id, get_active_session,
    get_active_pause, start_pause, stop_pause, get_session_pauses, WorkSession
)

"""
Обработчик команд учета времени
"""


router = Router()


# Состояния для FSM (Finite State Machine)
class PauseStates(StatesGroup):
    waiting_for_reason = State()  # Ожидаем причину паузы

@router.message(Command("start_work"))
async def cmd_start_work(message: types.Message):
    """Начать рабочий день"""

    user = message.from_user
    telegram_id = user.id

    # Получаем сессию БД
    db_get = get_db()
    db = next(db_get)

    try:
        # 1. Находим пользователя в БД
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await message.answer("⚠️ Сначала используйте /start для регистрации.")
            return

        # 2. Проверяем, нет ли активной сессии
        active_session = get_active_session(db, db_user.id)
        if active_session:
            start_time = active_session.start_time.strftime("%H:%M")
            await message.answer(
                f"⏰ Рабочий день уже начат в {start_time}!\n"
                f"Используйте /stop_work чтобы закончить."
            )
            return

        # 3. Создаем новую рабочую сессию
        new_session = WorkSession(
            user_id=db_user.id,
            start_time=datetime.utcnow(),
            date=datetime.utcnow(),
            description="Рабочий день начат"
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 4. Отправляем подтверждение
        start_time_local = new_session.start_time.strftime("%H:%M")
        await message.answer(
            f"✅ **Рабочий день начат!**\n"
            f"⏰ Время: {start_time_local}\n"
            f"📅 Дата: {new_session.date.strftime('%d.%m.%Y')}\n\n"
            f"💡 Теперь можно:\n"
            f"• /pause - сделать перерыв\n"
            f"• /stop_work - закончить день"
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при начале рабочего дня.")
        print(f"Ошибка start_work: {e}")

    finally:
        # Закрываем сессию БД
        next(db_get, None)

@router.message(Command("stop_work"))
async def cmd_stop_work(message: types.Message):
    """Закончить рабочий день"""

    user = message.from_user
    telegram_id = user.id

    # Получаем сессию БД
    db_get = get_db()
    db = next(db_get)

    try:

        # 1. Находим пользователя в БД.
        db_user = get_user_by_telegram_id(db=db, telegram_id=telegram_id)
        if not db_user:
            await message.answer("⚠️ Сначала используйте /start для регистрации.")
            return

        # 2. Находим активную сессию
        active_session = get_active_session(db, user_id=db_user.id)
        if not active_session:
            await message.answer("⚠️ У вас нет активного рабочего дня.\nИспользуйте /start_work чтобы начать.")
            return

        # 3. Завершаем сессию
        active_session.end_time = datetime.utcnow()
        db.commit()

        # 4. Рассчитываем время работы сессии
        if active_session.total_work_seconds:
            total_seconds = active_session.total_work_seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            work_duration = f"{hours}ч {minutes}мин"
        else:
            work_duration = "Не удалось рассчитать время"

        # 5. Отправляем отчет
        await message.answer(
            f"✅ **Рабочий день завершен!**\n\n"
            f"📊 **Статистика за день:**\n"
            f"⏱️ Начало: {active_session.start_time.strftime('%H:%M')}\n"
            f"⏱️ Конец: {active_session.end_time.strftime('%H:%M')}\n"
            f"⏱️ Общее время: {work_duration}\n"
            f"⏸️ Перерывы: {active_session.total_pause_seconds // 60} мин\n\n"
            f"🏁 Отличная работа! Хорошего отдыха!"
        )
    except Exception as e:
        await message.answer("❌ Произошла ошибка при завершении рабочего дня.")
        print(f"Ошибка stop_work: {e}")

    finally:
        next(db_get, None)


@router.message(Command("pause"))
async def cmd_pause(message: types.Message, state: FSMContext):
    """Начать/закончить перерыв"""

    telegram_id = message.from_user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Находим пользователя
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await message.answer("⚠️ Сначала используйте /start для регистрации.")
            return

        # 2. Проверяем активную сессию
        active_session = get_active_session(db, db_user.id)
        if not active_session:
            await message.answer(
                "⚠️ У вас нет активного рабочего дня.\n"
                "Используйте /start_work чтобы начать работу."
            )
            return

        # 3. Проверяем активную паузу
        active_pause = get_active_pause(db, active_session.id)

        if active_pause:
            # Есть активная пауза - завершаем ее
            stopped_pause = stop_pause(db, active_pause.id)

            if stopped_pause and stopped_pause.end_time:
                # Рассчитываем длительность паузы
                duration = stopped_pause.duration_seconds
                minutes = duration // 60 if duration else 0

                # Получаем все паузы сессии для статистики
                all_pauses = get_session_pauses(db, active_session.id)
                completed_pauses = [p for p in all_pauses if p.end_time]
                total_pause_minutes = active_session.total_pause_seconds // 60

                await message.answer(
                    f"✅ **Перерыв завершен!**\n\n"
                    f"⏸️ Длительность: {minutes} мин\n"
                    f"📝 Причина: {stopped_pause.reason or 'не указана'}\n\n"
                    f"📊 **Статистика по паузам:**\n"
                    f"• Всего перерывов: {len(completed_pauses)}\n"
                    f"• Общее время пауз: {total_pause_minutes} мин\n\n"
                    f"💪 Возвращайтесь к работе!"
                )
            else:
                await message.answer("❌ Не удалось завершить перерыв.")

        else:
            # Нет активной паузы - начинаем новую

            # Создаем клавиатуру с частыми причинами
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="☕ Кофе-брейк")],
                    [KeyboardButton(text="🍽️ Обед")],
                    [KeyboardButton(text="📞 Звонок")],
                    [KeyboardButton(text="🚬 Перекур")],
                    [KeyboardButton(text="🚫 Без причины")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )

            # Устанавливаем состояние ожидания причины
            await state.set_state(PauseStates.waiting_for_reason)
            await state.update_data(session_id=active_session.id)

            await message.answer(
                "⏸️ **Начинаем перерыв**\n\n"
                "Выберите причину или напишите свою:",
                reply_markup=keyboard
            )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при работе с перерывом.")
        print(f"Ошибка pause: {e}")

    finally:
        next(db_gen, None)


@router.message(PauseStates.waiting_for_reason)
async def process_pause_reason(message: types.Message, state: FSMContext):
    """Обработка причины паузы"""

    reason = message.text
    user_data = await state.get_data()
    session_id = user_data.get("session_id")

    db_gen = get_db()
    db = next(db_gen)

    try:
        # Создаем паузу с указанной причиной
        new_pause = start_pause(db, session_id, reason)

        await message.answer(
            f"✅ **Перерыв начат!**\n\n"
            f"⏸️ Причина: {reason}\n"
            f"⏰ Время начала: {new_pause.start_time.strftime('%H:%M')}\n\n"
            f"💡 Используйте /pause чтобы закончить перерыв.\n"
            f"🎯 Будьте продуктивны после отдыха!",
            reply_markup=types.ReplyKeyboardRemove()  # Убираем клавиатуру
        )

    except Exception as e:
        await message.answer("❌ Не удалось начать перерыв.")
        print(f"Ошибка process_pause_reason: {e}")

    finally:
        await state.clear()
        next(db_gen, None)


# Добавим команду для отмены
@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("ℹ️ Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=types.ReplyKeyboardRemove()
    )

