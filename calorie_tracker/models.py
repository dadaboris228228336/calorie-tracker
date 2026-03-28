from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class GoalMode(str, Enum):
    LOSS = "loss"        # похудение — дефицит калорий
    GAIN = "gain"        # набор массы — профицит калорий
    MAINTAIN = "maintain"  # поддержание веса


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"        # сидячий образ жизни
    LIGHT = "light"                # лёгкая активность 1–3 дня/нед
    MODERATE = "moderate"          # умеренная 3–5 дней/нед
    ACTIVE = "active"              # высокая 6–7 дней/нед
    VERY_ACTIVE = "very_active"    # очень высокая / спортсмен


@dataclass
class UserProfile:
    weight_kg: float        # вес в кг
    height_cm: float        # рост в см
    age: int                # возраст
    male: bool              # True = мужчина, False = женщина
    activity: ActivityLevel = ActivityLevel.MODERATE
    goal: GoalMode = GoalMode.MAINTAIN


@dataclass
class Entry:
    name: str           # название блюда (непустое, не только пробелы)
    calories: int       # 1..99_999
    timestamp: datetime # UTC, проставляется автоматически при создании


@dataclass
class DayStats:
    day: date
    entries: list[Entry]
    total: int


@dataclass
class WeekStats:
    week_start: date          # понедельник
    days: dict[date, int]     # дата → сумма калорий
    total: int
    daily_average: float


@dataclass
class MonthStats:
    year: int
    month: int
    days: dict[date, int]
    total: int
    daily_average: float


@dataclass
class YearStats:
    year: int
    months: dict[int, int]    # номер месяца → сумма калорий
    total: int
    monthly_average: float


class TrackerError(Exception):
    """Ошибки валидации трекера."""
    pass


class StorageError(Exception):
    """Ошибки чтения/записи хранилища."""
    pass
