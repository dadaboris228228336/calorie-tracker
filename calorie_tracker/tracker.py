from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from calorie_tracker.models import (
    ActivityLevel,
    DayStats,
    Entry,
    GoalMode,
    MonthStats,
    TrackerError,
    UserProfile,
    WeekStats,
    YearStats,
)
from calorie_tracker.storage import StorageProtocol

# Коэффициенты активности (PAL)
_ACTIVITY_FACTORS = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}

# Корректировка калорий по цели (ккал/день)
_GOAL_DELTA = {
    GoalMode.LOSS: -500,      # дефицит ~0.5 кг/нед
    GoalMode.MAINTAIN: 0,
    GoalMode.GAIN: +400,      # профицит ~0.4 кг/нед
}


class CalorieTracker:
    """Бизнес-логика трекера калорий."""

    def __init__(self, storage: StorageProtocol) -> None:
        self._storage = storage

    def add_entry(self, name: str, calories: int) -> None:
        """Валидирует входные данные, создаёт Entry и сохраняет через storage."""
        if not isinstance(calories, int) or not (1 <= calories <= 99_999):
            raise TrackerError(
                "Количество калорий должно быть целым числом в диапазоне от 1 до 99 999."
            )
        if not name or not name.strip():
            raise TrackerError("Название блюда не может быть пустым")

        entry = Entry(name=name, calories=calories, timestamp=datetime.now())
        self._storage.save(entry)

    def delete_entry(self, day: date, index: int) -> Entry:
        """Удаляет запись по индексу из указанного дня."""
        return self._storage.delete_entry(day, index)

    def get_goal_calories(self, profile: UserProfile) -> int:
        """Рассчитывает целевое количество калорий по формуле Миффлина-Сан Жеора + TDEE."""
        # Базовый обмен веществ (BMR)
        if profile.male:
            bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
        else:
            bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161
        # TDEE = BMR × коэффициент активности
        tdee = bmr * _ACTIVITY_FACTORS[profile.activity]
        # Целевые калории = TDEE + корректировка по цели
        goal_kcal = tdee + _GOAL_DELTA[profile.goal]
        return round(goal_kcal)

    def get_day_stats(self, day: date | None = None) -> DayStats:
        """Возвращает статистику за указанный день (по умолчанию — сегодня)."""
        if day is None:
            day = date.today()
        entries = self._storage.load_day(day)
        total = sum(e.calories for e in entries)
        return DayStats(day=day, entries=entries, total=total)

    def get_week_stats(self, week_date: date | None = None) -> WeekStats:
        """Возвращает статистику за неделю (пн–вс), содержащую week_date."""
        if week_date is None:
            week_date = date.today()
        week_start = week_date - timedelta(days=week_date.weekday())  # понедельник
        days: dict[date, int] = {}
        for i in range(7):
            d = week_start + timedelta(days=i)
            entries = self._storage.load_day(d)
            days[d] = sum(e.calories for e in entries)
        total = sum(days.values())
        daily_average = total / 7
        return WeekStats(week_start=week_start, days=days, total=total, daily_average=daily_average)

    def get_month_stats(self, year: int | None = None, month: int | None = None) -> MonthStats:
        """Возвращает статистику за указанный месяц (по умолчанию — текущий)."""
        today = date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        num_days = calendar.monthrange(year, month)[1]
        days: dict[date, int] = {}
        for d in range(1, num_days + 1):
            day = date(year, month, d)
            entries = self._storage.load_day(day)
            days[day] = sum(e.calories for e in entries)
        total = sum(days.values())
        daily_average = total / num_days
        return MonthStats(year=year, month=month, days=days, total=total, daily_average=daily_average)

    def get_year_stats(self, year: int | None = None) -> YearStats:
        """Возвращает статистику за указанный год (по умолчанию — текущий)."""
        if year is None:
            year = date.today().year
        months: dict[int, int] = {}
        for m in range(1, 13):
            num_days = calendar.monthrange(year, m)[1]
            month_total = 0
            for d in range(1, num_days + 1):
                entries = self._storage.load_day(date(year, m, d))
                month_total += sum(e.calories for e in entries)
            months[m] = month_total
        total = sum(months.values())
        monthly_average = total / 12
        return YearStats(year=year, months=months, total=total, monthly_average=monthly_average)
