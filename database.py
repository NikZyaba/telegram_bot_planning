# 1. Импорты стандартных библиотек
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 2. Импорты SQLAlchemy (ORM для работы с БД)
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.ext.declarative import declarative_base  # Для создания базового класса моделей
from sqlalchemy.orm import sessionmaker, scoped_session, Session, relationship  # Для работы с сессиями и связями
from sqlalchemy.exc import SQLAlchemyError  # Для отлова ошибок БД
from sqlalchemy import text  # Для теста

# 3. Импорт нашей конфигурации
from config import config

# 4. Создаем базовый класс для всех моделей
# Все классы-модели будут наследоваться от Base
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'  # Имя таблицы в БД

    # Поля таблицы:
    id = Column(Integer, primary_key=True)  # Автоинкрементный ID
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)  # Уникальный, не null, с индексом
    username = Column(String(100), nullable=True)  # Строка до 100 символов, может быть null
    first_name = Column(String(100), nullable=True)  # Строка до 100 символов, может быть null
    last_name = Column(String(100), nullable=True)  # Строка до 100 символов, может быть null
    is_admin = Column(Boolean, default=False)  # Булево значение, по умолчанию False (проверка на админа)
    created_at = Column(DateTime, default=datetime.utcnow)  # Автоматически при создании
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Обновляется при изменении

    # Связь один-ко-многим: один User → много WorkSession
    work_sessions = relationship("WorkSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):  # Строковое представление для отладки
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class WorkSession(Base):
    """Модель рабочей сессии (от начала до конца рабочего дня)"""
    # Наименование таблицы
    __tablename__ = "work_sessions"
    # Аргументы таблицы
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)  # Дата сессии
    start_time = Column(DateTime, nullable=False)  # Когда НАЧАЛ работать
    end_time = Column(DateTime, nullable=True)  # Когда ЗАКОНЧИЛ работать (null=True - если еще работает)
    description = Column(Text, nullable=True)  # Описание задачи
    total_pause_seconds = Column(Integer, default=0)  # Общее время пауз в секундах
    created_at = Column(DateTime, default=datetime.utcnow)

    """Связи"""
    user = relationship("User", back_populates="work_sessions")
    pauses = relationship("Pause", back_populates="work_session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkSession(id={self.id}, user_id={self.user_id}, date={self.date.date()})>"

    @property
    def is_active(self) -> bool:
        """Активна ли сессия (начата, но не завершена)"""
        return self.end_time is None

    @property
    def total_work_seconds(self) -> Optional[int]:
        """Общее время работы в секундах (без учета пауз)"""
        if self.end_time:
            total = (self.end_time - self.start_time).total_seconds()
            return int(total - self.total_pause_seconds)
        return None


class Pause(Base):
    """Модель паузы в работе"""
    __tablename__ = 'pauses'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('work_sessions.id', ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)  # NULL если пауза еще не завершена
    reason = Column(String(200), nullable=True)  # Причина паузы (обед, перекур и т.д.)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь
    work_session = relationship("WorkSession", back_populates="pauses")

    def __repr__(self):
        return f"<Pause(id={self.id}, session_id={self.session_id})>"

    @property
    def is_active(self) -> bool:
        """Активна ли пауза"""
        return self.end_time is None

    @property
    def duration_seconds(self) -> Optional[int]:
        """Длительность паузы в секундах"""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None


# ==================== ДВИЖОК И СЕССИИ ====================

# Создаем движок (подключение к БД)
engine = create_engine(
    config.db.url,  # URL из конфига, например "sqlite:///worktime.db"
    echo=config.db.echo,  # Если True, выводит все SQL-запросы в консоль
    pool_pre_ping=True,  # Проверяет живое ли соединение перед использованием
    connect_args={"check_same_thread": False} if "sqlite" in config.db.url else {}  # Для SQLite в многопоточке
)

# Создаем сессии
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Безопасность. Scoped session - гарантирует, что в одном потоке всегда одна и та же сессия
SessionScoped = scoped_session(SessionLocal)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_db() -> Session:
    """
    Генератор для получения сессии БД.
    Паттерн "Dependency Injection" (как в FastAPI).
    """
    db = SessionScoped()  # Создаем или получаем существующую сессию для этого потока
    try:
        yield db  # Отдаем сессию вызывающему коду
    finally:
        db.close()  # Гарантированно закрываем сессию в конце


def init_db():
    """Инициализация базы данных (создание всех таблиц)"""
    print(f"Инициализация БД по адресу: {config.db.url}")
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы успешно!")


def drop_db():
    """Удаление всех таблиц (только для разработки!)"""
    Base.metadata.drop_all(bind=engine)
    print("Все таблицы удалены!")


def add_user(
        db: Session,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
) -> User:
    """
    Добавить нового пользователя или получить существующего.
    Возвращает объект User
    """
    # Проверяем, существует ли пользователь
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        # Создаем нового
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Создан новый пользователь: {user}")
    else:
        # Обновляем данные существующего
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name

        user.updated_at = datetime.utcnow()
        db.commit()
        print(f"Обновлен пользователь: {user}")

    return user


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    """Найти пользователя по telegram_id"""
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def get_active_session(db: Session, user_id: int) -> Optional[WorkSession]:
    """
    Получить активную рабочую сессию пользователя
    (сессию, которая начата, но не завершена)
    """
    return db.query(WorkSession).filter(
        WorkSession.user_id == user_id,
        WorkSession.end_time.is_(None)
    ).first()

def create_work_session(db: Session, user_id: int, description: str) -> WorkSession:
    """Создаем новую рабочую сессию"""
    session = WorkSession(
        user_id=user_id,
        start_time=datetime.utcnow(),
        date=datetime.utcnow(),
        description=description
    )
    print(f"Новая рабочая сессия создана для пользователя id={user_id}")
    db.add(session)
    db.commit()
    db.refresh(session)
    print(f"Рабочая сессия добавлена в базу данных для пользователя id={user_id}")
    return session

def stop_work_session(db: Session, session_id: int) -> WorkSession:
    """Прекращаем работу сессии пользователя"""
    session = db.query(WorkSession).filter(WorkSession.id == session_id).first()
    if session:
        session.end_time = datetime.utcnow()
        db.commit()
        db.refresh(session)
    return session
#--------------------------------------------PAUSE-----------------------------------------------#
def start_pause(db: Session, session_id: int, reason: str = None) -> Pause:
    """Начать паузу в рабочей сессии"""
    pause = Pause(
        session_id=session_id,
        start_time=datetime.utcnow(),
        reason=reason
    )
    db.add(pause)
    db.commit()
    db.refresh(pause)
    return pause

def stop_pause(db: Session, pause_id: int) -> Pause:
    """Завершить паузу"""
    pause = db.query(Pause).filter(Pause.id == pause_id).first()
    if pause and pause.end_time is None:
        pause.end_time = datetime.utcnow()

    # Обновляем общее время пауз в сессии
    session = db.query(WorkSession).filter(WorkSession.id == pause.session_id).first()
    if session:
        pause_duration = (pause.end_time - pause.start_time).total_seconds()
        session.total_pause_seconds += int(pause_duration)

    db.commit()
    db.refresh(pause)
    return pause


def get_active_pause(db: Session, session_id: int) -> Optional[Pause]:
    """Получить активную паузу сессии"""
    return db.query(Pause).filter(
        Pause.session_id == session_id,
        Pause.end_time.is_(None)
    ).first()

def get_session_pauses(db: Session, session_id: int) -> List[Pause]:
    """Получить все паузы сессии"""
    return db.query(Pause).filter(Pause.session_id == session_id).all()

def get_today_pauses(db: Session, user_id: int) -> List[Pause]:
    """Получить все паузы пользователя за сегодня"""
    today = datetime.utcnow().date()

    # Находим все сессии пользователя за сегодня
    sessions = db.query(WorkSession).filter(
        WorkSession.user_id == user_id,
        WorkSession.date >= today
    ).all()

    # Берем все паузы с сессии
    all_pauses = list()
    for session in sessions:
        session_pauses = get_session_pauses(db=db, session_id=session.id)
        all_pauses.extend(session_pauses)

    return all_pauses

# ==================== ФУНКЦИИ СЕССИЙ ====================
def get_today_sessions(db: Session, user_id: int) -> List[WorkSession]:
    """Получить все сессии пользователя за сегодня"""
    today = datetime.utcnow().date()
    return db.query(WorkSession).filter(
        WorkSession.user_id == user_id,
        WorkSession.date >= today,
        WorkSession.end_time.isnot(None)  # Только завершенные
    ).all()

def get_week_sessions(db: Session, user_id: int) -> List[WorkSession]:
    """Получить все сессии пользователя за последние 7 дней"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    return db.query(WorkSession).filter(
        WorkSession.user_id == user_id,
        WorkSession.created_at >= week_ago,
        WorkSession.end_time.isnot(None)
    ).all()

def calculate_session_stats(session: WorkSession) -> Dict[str, Any]:
    """Рассчитать статистику для одной сессии"""
    if not session.end_time or session.total_work_seconds is None:
        return {}

    total_seconds = session.total_work_seconds
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    pause_minutes = session.total_pause_seconds // 60

    # Расчет продуктивности (время работы / (время работы + паузы))
    if total_seconds + session.total_pause_seconds > 0:
        productivity = int((total_seconds / (total_seconds + session.total_pause_seconds)) * 100)
    else:
        productivity = 0

    return {
        'date': session.date.strftime('%d.%m.%Y'),
        'start': session.start_time.strftime('%H:%M'),
        'end': session.end_time.strftime('%H:%M'),
        'work_hours': hours,
        'work_minutes': minutes,
        'pause_minutes': pause_minutes,
        'productivity': productivity,
        'description': session.description
    }


def calculate_daily_stats(sessions: List[WorkSession]) -> Dict[str, Any]:
    """Рассчитать общую статистику за день"""
    if not sessions:
        return {
            'total_work_seconds': 0,
            'total_pause_seconds': 0,
            'sessions_count': 0,
            'productivity': 0
        }

    total_work = sum(s.total_work_seconds or 0 for s in sessions)
    total_pause = sum(s.total_pause_seconds or 0 for s in sessions)

    if total_work + total_pause > 0:
        productivity = int((total_work / (total_work + total_pause)) * 100)
    else:
        productivity = 0

    total_hours = total_work // 3600
    total_minutes = (total_work % 3600) // 60
    total_pause_minutes = total_pause // 60

    return {
        'total_work_seconds': total_work,
        'total_work_hours': total_hours,
        'total_work_minutes': total_minutes,
        'total_pause_seconds': total_pause,
        'total_pause_minutes': total_pause_minutes,
        'sessions_count': len(sessions),
        'productivity': productivity
    }



# ==================== ТЕСТОВЫЕ ФУНКЦИИ ====================
def test_connection():
    """Тест подключения к БД"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Подключение к БД успешно!")
        return True
    except SQLAlchemyError as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False


if __name__ == "__main__":
    # При запуске файла напрямую инициализируем БД
    print("=== Инициализация базы данных ===")
    test_connection()
    init_db()
    print("=== Готово! ===")
