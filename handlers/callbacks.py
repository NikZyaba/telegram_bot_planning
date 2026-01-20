from datetime import datetime
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from keyboards.main_menu import get_main_menu, get_stats_menu
from database import (get_db, get_user_by_telegram_id, get_active_session, WorkSession,
                      get_session_pauses, get_active_pause, stop_pause, start_pause)

"""
Обработчики callback-запросов от инлайн-кнопок
"""

router = Router()


@router.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    """Показать главное меню"""
    await callback.message.edit_text(
        "🤖 **Главное меню**\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "start_work")
async def process_start_work(callback: types.CallbackQuery):
    """Обработка кнопки 'Начать день'"""

    # ВАЖНО: берем пользователя из callback, а не из сообщения
    user = callback.from_user
    telegram_id = user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Находим пользователя в БД
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await callback.message.answer("⚠️ Сначала используйте /start для регистрации.")
            await callback.answer()
            return

        # 2. Проверяем, нет ли активной сессии
        active_session = get_active_session(db, db_user.id)
        if active_session:
            start_time = active_session.start_time.strftime("%H:%M")
            await callback.message.answer(
                f"⏰ Рабочий день уже начат в {start_time}!\n"
                f"Используйте 'Завершить день' чтобы закончить."
            )
            await callback.answer()
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
        await callback.message.answer(
            f"✅ **Рабочий день начат!**\n"
            f"⏰ Время: {start_time_local}\n"
            f"📅 Дата: {new_session.date.strftime('%d.%m.%Y')}\n\n"
            f"💡 Теперь можно:\n"
            f"• Использовать кнопку 'Пауза' для перерыва\n"
            f"• Использовать кнопку 'Завершить день' для окончания"
        )

        # 5. Показываем меню
        await callback.message.answer(
            "👇 Используйте меню для дальнейших действий:",
            reply_markup=get_main_menu()
        )

        await callback.answer("✅ День начат!")

    except Exception as e:
        await callback.message.answer("❌ Произошла ошибка при начале рабочего дня.")
        print(f"Ошибка start_work (callback): {e}")

    finally:
        # Закрываем сессию БД
        next(db_gen, None)


@router.callback_query(lambda c: c.data == "stop_work")
async def process_stop_work(callback: types.CallbackQuery):
    """Обработка кнопки 'Завершить день'"""

    # ВАЖНО: берем пользователя из callback
    user = callback.from_user
    telegram_id = user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Находим пользователя
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await callback.message.answer("⚠️ Сначала используйте /start для регистрации.")
            await callback.answer()
            return

        # 2. Находим активную сессию
        active_session = get_active_session(db, db_user.id)
        if not active_session:
            await callback.message.answer(
                "⚠️ У вас нет активного рабочего дня.\n"
                "Используйте 'Начать день' чтобы начать."
            )
            await callback.answer()
            return

        # 3. Завершаем сессию
        active_session.end_time = datetime.utcnow()
        db.commit()

        # 4. Рассчитываем время работы
        if active_session.total_work_seconds:
            total_seconds = active_session.total_work_seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            work_duration = f"{hours}ч {minutes}мин"
        else:
            work_duration = "не удалось рассчитать"

        # 5. Отправляем отчет
        await callback.message.answer(
            f"✅ **Рабочий день завершен!**\n\n"
            f"📊 **Статистика за день:**\n"
            f"⏱️ Начало: {active_session.start_time.strftime('%H:%M')}\n"
            f"⏱️ Конец: {active_session.end_time.strftime('%H:%M')}\n"
            f"⏱️ Общее время: {work_duration}\n"
            f"⏸️ Перерывы: {active_session.total_pause_seconds // 60} мин\n\n"
            f"🏁 Отличная работа! Хорошего отдыха!"
        )

        await callback.answer("✅ День завершен!")

    except Exception as e:
        await callback.message.answer("❌ Произошла ошибка при завершении рабочего дня.")
        print(f"Ошибка stop_work (callback): {e}")

    finally:
        next(db_gen, None)


@router.callback_query(lambda c: c.data == "pause")
async def process_pause(callback: types.CallbackQuery):
    """Обработка кнопки 'Пауза' - основная логика"""

    user = callback.from_user
    telegram_id = user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Находим пользователя
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await callback.message.answer("⚠️ Сначала используйте /start для регистрации.")
            await callback.answer()
            return

        # 2. Проверяем активную сессию
        active_session = get_active_session(db, db_user.id)
        if not active_session:
            await callback.message.answer(
                "⚠️ У вас нет активного рабочего дня.\n"
                "Используйте 'Начать день' чтобы начать работу."
            )
            await callback.answer()
            return

        # 3. Проверяем активную паузу
        active_pause = get_active_pause(db, active_session.id)

        if active_pause:
            # Есть активная пауза - завершаем ее
            stopped_pause = stop_pause(db, active_pause.id)

            if stopped_pause and stopped_pause.end_time:
                # Рассчитываем длительность паузы
                duration_seconds = stopped_pause.duration_seconds
                minutes = duration_seconds // 60 if duration_seconds else 0
                seconds = duration_seconds % 60 if duration_seconds else 0

                # Получаем статистику пауз за сессию
                all_pauses = get_session_pauses(db, active_session.id)
                completed_pauses = [p for p in all_pauses if p.end_time]

                await callback.message.answer(
                    f"✅ **Перерыв завершен!**\n\n"
                    f"⏱️ Длительность: {minutes} мин {seconds} сек\n"
                    f"📝 Причина: {stopped_pause.reason or 'не указана'}\n\n"
                    f"📊 **Статистика по паузам:**\n"
                    f"• Перерывов в этой сессии: {len(completed_pauses)}\n"
                    f"• Общее время пауз: {active_session.total_pause_seconds // 60} мин\n\n"
                    f"💪 Возвращайтесь к работе!"
                )
            else:
                await callback.message.answer("❌ Не удалось завершить перерыв.")

            await callback.answer()

        else:
            # Нет активной паузы - начинаем новую
            from keyboards.pause_reasons import get_pause_reasons_keyboard

            await callback.message.answer(
                "⏸️ **Начинаем перерыв**\n\n"
                "Выберите причину перерыва:",
                reply_markup=get_pause_reasons_keyboard()
            )
            await callback.answer()

    except Exception as e:
        await callback.message.answer("❌ Произошла ошибка при работе с перерывом.")
        print(f"Ошибка pause: {e}")

    finally:
        next(db_gen, None)

@router.callback_query(lambda c: c.data.startswith("pause_reason:"))
async def process_pause_reason(callback:types.CallbackQuery):
    """Обработка выбора причины паузы"""

    # Получаем причину паузы
    reason_code = callback.data.split(":")[1]

    # Список причин
    reason_map = {
        "coffee": "☕ Кофе-брейк",
        "lunch": "🍽️ Обед",
        "call": "📞 Звонок/встреча",
        "technical": "💻 Технический перерыв",
        "smoke": "🚬 Перекур",
        "away": "🚶 Отлучился",
        "none": "🎯 Без причины"
    }
    reason_text = reason_map.get(reason_code, "Не указана")

    user = callback.from_user
    telegram_id = user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # Находим пользователя
        db_user = get_user_by_telegram_id(db=db, telegram_id=telegram_id)
        if not db_user:
            await callback.message.answer("⚠️ Ошибка: пользователь не найден.")
            await callback.answer()
            return

        # Находим активную сессию
        active_session = get_active_session(db, db_user.id)
        if not active_session:
            await callback.message.answer("⚠️ Нет активной рабочей сессии.")
            await callback.answer()
            return

        # Создаем паузу с выбранной причиной
        new_pause = start_pause(db=db, session_id=active_session.id, reason=reason_text)

        from keyboards.pause_reasons import get_pause_actions_keyboard

        await callback.message.edit_text(
            f"✅ **Перерыв начат!**\n\n"
            f"⏸️ Причина: {reason_text}\n"
            f"⏰ Время начала: {new_pause.start_time.strftime('%H:%M:%S')}\n\n"
            f"💡 Используйте кнопку 'Пауза' чтобы завершить перерыв.",
            reply_markup=get_pause_actions_keyboard()
        )

        await callback.answer()

    except Exception as e:
        await callback.message.answer("❌ Не удалось начать перерыв.")
        print(f"Ошибка process_pause_reason: {e}")

    finally:
        next(db_gen, None)


@router.callback_query(lambda c: c.data == "pause_cancel")
async def process_pause_cancel(callback: types.CallbackQuery):
    """Отмена начала перерыва"""
    await callback.message.edit_text(
        "❌ **Начало перерыва отменено**\n\n"
        "Вы можете продолжить работу.\n"
        "Для перерыва нажмите кнопку 'Пауза' еще раз."
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "pause_stop")
async def process_pause_stop(callback: types.CallbackQuery):
    """Завершить перерыв из меню паузы"""
    await process_pause(callback)


@router.callback_query(lambda c: c.data == "pause_info")
async def process_pause_info(callback: types.CallbackQuery):
    """Информация о текущей паузе"""

    user = callback.from_user
    telegram_id = user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Находим пользователя
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await callback.message.answer("⚠️ Ошибка: пользователь не найден.")
            await callback.answer()
            return

        # 2. Находим активную сессию
        active_session = get_active_session(db, db_user.id)
        if not active_session:
            await callback.message.answer("⚠️ Нет активной рабочей сессии.")
            await callback.answer()
            return

        # 3. Находим активную паузу
        active_pause = get_active_pause(db, active_session.id)

        if not active_pause:
            await callback.message.answer("ℹ️ **Нет активного перерыва**\n\nСейчас вы не на перерыве.")
            await callback.answer()
            return

        # 4. Рассчитываем длительность текущей паузы
        now = datetime.utcnow()
        duration = now - active_pause.start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)

        # 5. Получаем статистику по всем паузам сессии
        all_pauses = get_session_pauses(db, active_session.id)
        completed_pauses = [p for p in all_pauses if p.end_time]

        await callback.message.answer(
            f"ℹ️ **Информация о перерыве**\n\n"
            f"⏸️ Причина: {active_pause.reason or 'не указана'}\n"
            f"⏰ Начало: {active_pause.start_time.strftime('%H:%M:%S')}\n"
            f"⏱️ Прошло: {minutes} мин {seconds} сек\n\n"
            f"📊 **Статистика за сессию:**\n"
            f"• Всего перерывов: {len(completed_pauses)}\n"
            f"• Активный перерыв: 1\n"
            f"• Общее время пауз: {active_session.total_pause_seconds // 60} мин\n\n"
            f"💡 Нажмите 'Пауза' чтобы завершить перерыв."
        )

        await callback.answer()

    except Exception as e:
        await callback.message.answer("❌ Ошибка при получении информации о паузе.")
        print(f"Ошибка pause_info: {e}")

    finally:
        next(db_gen, None)



@router.callback_query(lambda c: c.data == "stats_menu")
async def process_stats_menu(callback: types.CallbackQuery):
    """Показать меню статистики"""
    await callback.message.edit_text(
        "📊 **Меню статистики**\n\n"
        "Выберите период:",
        reply_markup=get_stats_menu()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats_today")
async def process_stats_today(callback: types.CallbackQuery):
    """Статистика за сегодня"""
    await callback.message.answer(
        "📊 **Статистика за сегодня**\n\n"
        "Эта функция в разработке.\n"
        "Используйте команду /today для полной статистики."
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats_week")
async def process_stats_week(callback: types.CallbackQuery):
    """Статистика за неделю"""
    await callback.message.answer(
        "📅 **Статистика за неделю**\n\n"
        "Эта функция в разработке.\n"
        "Используйте команду /week для полной статистики."
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "help")
async def process_help(callback: types.CallbackQuery):
    """Показать помощь"""
    # Импортируем здесь, чтобы избежать циклических импортов
    from handlers.start import cmd_help
    await cmd_help(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings")
async def process_settings(callback: types.CallbackQuery):
    """Настройки (заглушка)"""
    await callback.message.answer(
        "⚙️ **Настройки**\n\n"
        "Эта функция находится в разработке.\n"
        "Скоро здесь можно будет:\n"
        "• Изменить часовой пояс\n"
        "• Настроить уведомления\n"
        "• Установить цели на день"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats_month")
async def process_stats_month(callback: types.CallbackQuery):
    """Статистика за месяц (заглушка)"""
    await callback.message.answer(
        "📈 **Статистика за месяц**\n\n"
        "Эта функция находится в разработке.\n"
        "Скоро здесь будет детальная статистика за месяц."
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats_all")
async def process_stats_all(callback: types.CallbackQuery):
    """Статистика за все время (заглушка)"""
    await callback.message.answer(
        "📊 **Статистика за все время**\n\n"
        "Эта функция находится в разработке.\n"
        "Скоро здесь будет полная история вашей работы."
    )
    await callback.answer()


@router.callback_query()
async def process_unknown_callback(callback: types.CallbackQuery):
    """Обработка неизвестных callback-запросов"""
    await callback.answer("⚠️ Неизвестная команда", show_alert=True)
