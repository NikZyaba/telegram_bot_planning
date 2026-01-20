from aiogram import Router, types
from aiogram.filters import Command
from keyboards.main_menu import get_main_menu

from datetime import datetime, timedelta
from database import (
    get_db, get_user_by_telegram_id, get_active_session,
    get_today_sessions, get_week_sessions,
    calculate_session_stats, calculate_daily_stats
)
router = Router()


"""
Обработчик команд статистики
"""


@router.message(Command("today"))
async def cmd_today(message: types.Message):
    """Статистика за сегодня"""

    # Получаем id пользователя ТГ
    telegram_id = message.from_user.id

    # Получаем сессию БД
    db_get = get_db()
    db = next(db_get)

    try:
        # Ищем пользователя в БД
        db_user = get_user_by_telegram_id(db=db, telegram_id=telegram_id)
        if not db_user:
            await message.answer("⚠️ Сначала используйте /start для регистрации.")
            return
        # Проверяем активную сессию
        active_session = get_active_session(db=db, user_id=db_user.id)
        # Получаем сессии за сегодня
        today_sessions = get_today_sessions(db=db, user_id=db_user.id)

        # Рассчитываем статистику
        daily_stats = calculate_daily_stats(sessions=today_sessions)

        # Готовим ответ
        response_lines = [
            f"📊 **СТАТИСТИКА ЗА СЕГОДНЯ** ({datetime.now().strftime('%d.%m.%Y')})",]

        # Ксли есть активная сессия
        if active_session:
            active_time = datetime.utcnow() - active_session.start_time
            active_hours = int(active_time.total_seconds() // 3600)
            active_minutes = int((active_time.total_seconds() % 3600) // 60)

            response_lines.extend([
                f"⚡ **АКТИВНАЯ СЕССИЯ:**",
                f"⏱️ Начата: {active_session.start_time.strftime('%H:%M')}",
                f"⏱️ Прошло: {active_hours}ч {active_minutes}мин",
                f"⏸️ Паузы: {active_session.total_pause_seconds // 60} мин",
                ""
            ])

        if today_sessions:
            # Выводим детали по каждой завершенной сессии
            response_lines.append("✅ **ЗАВЕРШЕННЫЕ СЕССИИ:**")

            for i, session in enumerate(today_sessions, 1):
                stats = calculate_session_stats(session)
                if stats:
                    response_lines.append(
                        f"{i}. {stats['start']}-{stats['end']}: "
                        f"{stats['work_hours']}ч {stats['work_minutes']}мин работы, "
                        f"{stats['pause_minutes']}мин пауз"
                    )

            response_lines.append("")

        # Общая статистика
        response_lines.extend([
            f"📈 **ОБЩАЯ СТАТИСТИКА:**",
            f"📅 Сессий сегодня: {daily_stats['sessions_count']}",
            f"⏱️ Общее время работы: {daily_stats['total_work_hours']}ч {daily_stats['total_work_minutes']}мин",
            f"⏸️ Общее время пауз: {daily_stats['total_pause_minutes']}мин",
            f"📊 Продуктивность: {daily_stats['productivity']}%",
        ])

        if not active_session and not today_sessions:
            response_lines.append("\nℹ️ Сегодня еще не было рабочих сессий.")

        await message.answer("\n".join(response_lines))
        await message.answer(
            "🔙 Возврат в главное меню:",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        await message.answer("❌ Ошибка при получении статистики.")
        print(f"Ошибка today: {e}")

    finally:
        next(db_get, None)


@router.message(Command("week"))
async def cmd_week(message: types.Message):
    """Статистика за неделю"""

    telegram_id = message.from_user.id

    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Находим пользователя
        db_user = get_user_by_telegram_id(db, telegram_id)
        if not db_user:
            await message.answer("⚠️ Сначала используйте /start для регистрации.")
            return

        # 2. Получаем сессии за неделю
        week_sessions = get_week_sessions(db, db_user.id)

        if not week_sessions:
            await message.answer(
                "📅 **СТАТИСТИКА ЗА НЕДЕЛЮ**\n\n"
                "ℹ️ За последние 7 дней не было рабочих сессий.\n"
                "Используйте /start_work чтобы начать учет времени."
            )
            return

        # 3. Группируем по дням
        daily_data = {}
        for session in week_sessions:
            date_str = session.date.strftime('%d.%m.%Y')
            if date_str not in daily_data:
                daily_data[date_str] = []
            daily_data[date_str].append(session)

        # 4. Рассчитываем статистику
        total_work_seconds = 0
        total_pause_seconds = 0

        response_lines = [
            "📅 **СТАТИСТИКА ЗА НЕДЕЛЮ**",
            f"📆 Период: последние 7 дней",
            ""
        ]

        # Статистика по дням
        for date_str, sessions in sorted(daily_data.items(), reverse=True):
            day_stats = calculate_daily_stats(sessions)

            total_work_seconds += day_stats['total_work_seconds']
            total_pause_seconds += day_stats['total_pause_seconds']

            response_lines.append(
                f"📅 **{date_str}** ({day_stats['sessions_count']} сессий):\n"
                f"   ⏱️ Работа: {day_stats['total_work_hours']}ч {day_stats['total_work_minutes']}мин\n"
                f"   ⏸️ Паузы: {day_stats['total_pause_minutes']}мин\n"
                f"   📊 Продуктивность: {day_stats['productivity']}%"
            )

        # Итоговая статистика
        total_work_hours = total_work_seconds // 3600
        total_work_minutes = (total_work_seconds % 3600) // 60
        total_pause_minutes = total_pause_seconds // 60

        if total_work_seconds + total_pause_seconds > 0:
            total_productivity = int((total_work_seconds / (total_work_seconds + total_pause_seconds)) * 100)
        else:
            total_productivity = 0

        response_lines.extend([
            "",
            "📈 **ИТОГО ЗА НЕДЕЛЮ:**",
            f"📅 Всего дней: {len(daily_data)}",
            f"📊 Всего сессий: {len(week_sessions)}",
            f"⏱️ Общее время работы: {total_work_hours}ч {total_work_minutes}мин",
            f"⏸️ Общее время пауз: {total_pause_minutes}мин",
            f"📊 Средняя продуктивность: {total_productivity}%",
            "",
            "💡 **Совет:** Старайтесь сохранять продуктивность выше 80%!"
        ])

        await message.answer("\n".join(response_lines))
        await message.answer(
            "🔙 Возврат в главное меню:",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        await message.answer("❌ Ошибка при получении статистики за неделю.")
        print(f"Ошибка week: {e}")

    finally:
        next(db_gen, None)