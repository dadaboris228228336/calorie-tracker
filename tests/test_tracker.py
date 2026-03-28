from __future__ import annotations

from datetime import date, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from calorie_tracker.models import Entry, TrackerError
from calorie_tracker.tracker import CalorieTracker


# --- Fake storage для изоляции тестов ---

class FakeStorage:
    """In-memory хранилище для тестов (не пишет на диск)."""

    def __init__(self) -> None:
        self.saved: list[Entry] = []

    def save(self, entry: Entry) -> None:
        self.saved.append(entry)

    def load_day(self, day: date) -> list[Entry]:
        return [e for e in self.saved if e.timestamp.date() == day]


# --- Property-тесты ---

# Feature: calorie-tracker, Property 1: Round-trip добавления записи
# Validates: Requirements 1.1, 6.5
@settings(max_examples=100)
@given(
    name=st.text(min_size=1).filter(lambda s: s.strip() != ""),
    calories=st.integers(1, 99_999),
)
def test_add_entry_round_trip(name: str, calories: int) -> None:
    """Свойство 1: после add_entry запись с теми же name и calories присутствует в хранилище."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)

    tracker.add_entry(name, calories)

    today = datetime.now().date()
    day_entries = storage.load_day(today)

    assert any(
        e.name == name and e.calories == calories
        for e in day_entries
    ), f"Запись name={name!r}, calories={calories} не найдена в хранилище"


# Feature: calorie-tracker, Property 2: Невалидные калории отклоняются
# Validates: Requirements 1.2, 1.4
@settings(max_examples=100)
@given(
    calories=st.one_of(st.integers(max_value=0), st.integers(min_value=100_000)),
)
def test_invalid_calories_rejected(calories: int) -> None:
    """Свойство 2: add_entry бросает TrackerError для калорий ≤ 0 или ≥ 100 000 и не сохраняет запись."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)

    with pytest.raises(TrackerError):
        tracker.add_entry("Тест", calories)

    assert len(storage.saved) == 0, "Запись не должна быть сохранена при невалидных калориях"


# Feature: calorie-tracker, Property 3: Пустое или пробельное название отклоняется
# Validates: Requirements 1.3
@settings(max_examples=100)
@given(
    name=st.one_of(
        st.just(""),
        st.text(alphabet=st.characters(whitelist_categories=("Zs",))),
    ),
)
def test_blank_name_rejected(name: str) -> None:
    """Свойство 3: add_entry бросает TrackerError с нужным сообщением для пустого/пробельного названия."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)

    with pytest.raises(TrackerError, match="Название блюда не может быть пустым"):
        tracker.add_entry(name, 100)

    assert len(storage.saved) == 0, "Запись не должна быть сохранена при пустом названии"

# --- Property-тесты для агрегации и средних значений (задача 3.7) ---

import calendar
from datetime import timedelta

from calorie_tracker.models import DayStats, MonthStats, WeekStats, YearStats


def make_entry(name: str, calories: int, day: date) -> Entry:
    return Entry(name=name, calories=calories, timestamp=datetime(day.year, day.month, day.day, 12, 0, 0))


# Feature: calorie-tracker, Property 4: Корректность агрегации по периодам
# Validates: Requirements 2.1, 3.1, 4.1, 5.1
@settings(max_examples=100)
@given(
    entries_data=st.lists(
        st.tuples(
            st.text(min_size=1).filter(lambda s: s.strip() != ""),
            st.integers(1, 99_999),
        ),
        max_size=20,
    )
)
def test_aggregation_correctness(entries_data: list[tuple[str, int]]) -> None:
    """Свойство 4: total в статистике равен сумме calories всех записей периода."""
    today = date(2024, 6, 15)  # суббота
    storage = FakeStorage()
    for name, cal in entries_data:
        storage.save(make_entry(name, cal, today))

    tracker = CalorieTracker(storage)

    # День
    day_stats = tracker.get_day_stats(today)
    assert day_stats.total == sum(c for _, c in entries_data)

    # Неделя (все записи в один день недели)
    week_stats = tracker.get_week_stats(today)
    assert week_stats.total == sum(c for _, c in entries_data)

    # Месяц
    month_stats = tracker.get_month_stats(2024, 6)
    assert month_stats.total == sum(c for _, c in entries_data)

    # Год
    year_stats = tracker.get_year_stats(2024)
    assert year_stats.total == sum(c for _, c in entries_data)


# Feature: calorie-tracker, Property 5: Корректность вычисления среднего
# Validates: Requirements 3.3, 4.3, 5.3
@settings(max_examples=100)
@given(
    entries_data=st.lists(
        st.tuples(
            st.text(min_size=1).filter(lambda s: s.strip() != ""),
            st.integers(1, 99_999),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_average_correctness(entries_data: list[tuple[str, int]]) -> None:
    """Свойство 5: daily_average = total/7 для недели, total/days_in_month для месяца, total/12 для года."""
    today = date(2024, 6, 15)
    storage = FakeStorage()
    for name, cal in entries_data:
        storage.save(make_entry(name, cal, today))

    tracker = CalorieTracker(storage)
    total = sum(c for _, c in entries_data)

    week_stats = tracker.get_week_stats(today)
    assert abs(week_stats.daily_average - total / 7) < 1e-9

    month_stats = tracker.get_month_stats(2024, 6)
    days_in_june = 30
    assert abs(month_stats.daily_average - total / days_in_june) < 1e-9

    year_stats = tracker.get_year_stats(2024)
    assert abs(year_stats.monthly_average - total / 12) < 1e-9


# Feature: calorie-tracker, Property 6: Пустой период возвращает нулевую сумму
# Validates: Requirements 2.3, 3.4, 4.4, 5.4
@settings(max_examples=50)
@given(day=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)))
def test_empty_period_returns_zero(day: date) -> None:
    """Свойство 6: при отсутствии записей total == 0 для любого периода."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)

    assert tracker.get_day_stats(day).total == 0
    assert tracker.get_week_stats(day).total == 0
    assert tracker.get_month_stats(day.year, day.month).total == 0
    assert tracker.get_year_stats(day.year).total == 0


# --- Unit-тесты для методов трекера (задача 3.8) ---

def test_get_day_stats_default_is_today() -> None:
    """get_day_stats() без аргументов использует сегодняшнюю дату."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    tracker.add_entry("Яблоко", 80)
    stats = tracker.get_day_stats()
    assert stats.day == date.today()
    assert stats.total == 80


def test_get_week_stats_default_is_current_week() -> None:
    """get_week_stats() без аргументов использует текущую неделю."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    tracker.add_entry("Банан", 90)
    stats = tracker.get_week_stats()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    assert stats.week_start == week_start
    assert stats.total == 90


def test_get_month_stats_default_is_current_month() -> None:
    """get_month_stats() без аргументов использует текущий месяц."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    tracker.add_entry("Суп", 200)
    stats = tracker.get_month_stats()
    today = date.today()
    assert stats.year == today.year
    assert stats.month == today.month
    assert stats.total == 200


def test_get_year_stats_default_is_current_year() -> None:
    """get_year_stats() без аргументов использует текущий год."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    tracker.add_entry("Каша", 300)
    stats = tracker.get_year_stats()
    assert stats.year == date.today().year
    assert stats.total == 300


def test_empty_day_returns_zero_and_empty_list() -> None:
    """Пустой день: total=0, entries=[]."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    stats = tracker.get_day_stats(date(2020, 1, 1))
    assert stats.total == 0
    assert stats.entries == []


def test_week_boundaries_monday_to_sunday() -> None:
    """Неделя начинается в понедельник и заканчивается в воскресенье."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    # 2024-06-10 — понедельник
    monday = date(2024, 6, 10)
    sunday = date(2024, 6, 16)
    storage.save(make_entry("Завтрак", 400, monday))
    storage.save(make_entry("Ужин", 600, sunday))
    stats = tracker.get_week_stats(monday)
    assert stats.week_start == monday
    assert stats.total == 1000
    assert len(stats.days) == 7


def test_leap_year_february_has_29_days() -> None:
    """Февраль високосного года содержит 29 дней в статистике."""
    storage = FakeStorage()
    tracker = CalorieTracker(storage)
    stats = tracker.get_month_stats(2024, 2)  # 2024 — високосный
    assert len(stats.days) == 29


# --- Тесты для delete_entry ---

class FakeStorageWithDelete(FakeStorage):
    """FakeStorage с поддержкой delete_entry."""

    def delete_entry(self, day: date, index: int) -> Entry:
        from calorie_tracker.models import StorageError
        entries = self.load_day(day)
        if index < 0 or index >= len(entries):
            raise StorageError(f"Запись с индексом {index} не найдена")
        # Удаляем из self.saved по совпадению объекта
        target = entries[index]
        self.saved.remove(target)
        return target


def test_delete_entry_removes_correct_entry() -> None:
    """delete_entry удаляет запись по индексу и возвращает её."""
    storage = FakeStorageWithDelete()
    tracker = CalorieTracker(storage)
    today = date(2024, 6, 15)
    storage.save(make_entry("Завтрак", 300, today))
    storage.save(make_entry("Обед", 600, today))
    storage.save(make_entry("Ужин", 400, today))

    removed = tracker.delete_entry(today, 1)  # удаляем "Обед"

    assert removed.name == "Обед"
    assert removed.calories == 600
    remaining = storage.load_day(today)
    assert len(remaining) == 2
    assert all(e.name != "Обед" for e in remaining)


def test_delete_entry_invalid_index_raises() -> None:
    """delete_entry с невалидным индексом бросает StorageError."""
    from calorie_tracker.models import StorageError
    storage = FakeStorageWithDelete()
    tracker = CalorieTracker(storage)
    today = date(2024, 6, 15)
    storage.save(make_entry("Завтрак", 300, today))

    with pytest.raises(StorageError):
        tracker.delete_entry(today, 5)


def test_delete_entry_empty_day_raises() -> None:
    """delete_entry на пустой день бросает StorageError."""
    from calorie_tracker.models import StorageError
    storage = FakeStorageWithDelete()
    tracker = CalorieTracker(storage)

    with pytest.raises(StorageError):
        tracker.delete_entry(date(2024, 1, 1), 0)


# --- Тесты для get_goal_calories ---

from calorie_tracker.models import ActivityLevel, GoalMode, UserProfile


def test_goal_calories_male_moderate_maintain() -> None:
    """Расчёт нормы для мужчины с умеренной активностью, поддержание веса."""
    tracker = CalorieTracker(FakeStorage())
    profile = UserProfile(
        weight_kg=80, height_cm=180, age=30,
        male=True, activity=ActivityLevel.MODERATE, goal=GoalMode.MAINTAIN
    )
    # BMR = 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
    # TDEE = 1780 * 1.55 = 2759
    goal = tracker.get_goal_calories(profile)
    assert goal == round(1780 * 1.55)


def test_goal_calories_female_sedentary_loss() -> None:
    """Расчёт нормы для женщины с сидячим образом жизни, похудение."""
    tracker = CalorieTracker(FakeStorage())
    profile = UserProfile(
        weight_kg=60, height_cm=165, age=25,
        male=False, activity=ActivityLevel.SEDENTARY, goal=GoalMode.LOSS
    )
    # BMR = 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
    # TDEE = 1345.25 * 1.2 = 1614.3
    # goal = 1614.3 - 500 = 1114.3
    goal = tracker.get_goal_calories(profile)
    bmr = 10 * 60 + 6.25 * 165 - 5 * 25 - 161
    expected = round(bmr * 1.2 - 500)
    assert goal == expected


def test_goal_calories_gain_adds_400() -> None:
    """Режим набора массы добавляет +400 ккал к TDEE."""
    tracker = CalorieTracker(FakeStorage())
    profile_maintain = UserProfile(
        weight_kg=75, height_cm=175, age=28,
        male=True, activity=ActivityLevel.MODERATE, goal=GoalMode.MAINTAIN
    )
    profile_gain = UserProfile(
        weight_kg=75, height_cm=175, age=28,
        male=True, activity=ActivityLevel.MODERATE, goal=GoalMode.GAIN
    )
    maintain_kcal = tracker.get_goal_calories(profile_maintain)
    gain_kcal = tracker.get_goal_calories(profile_gain)
    assert gain_kcal == maintain_kcal + 400


def test_goal_calories_loss_subtracts_500() -> None:
    """Режим похудения вычитает -500 ккал из TDEE."""
    tracker = CalorieTracker(FakeStorage())
    profile_maintain = UserProfile(
        weight_kg=75, height_cm=175, age=28,
        male=True, activity=ActivityLevel.MODERATE, goal=GoalMode.MAINTAIN
    )
    profile_loss = UserProfile(
        weight_kg=75, height_cm=175, age=28,
        male=True, activity=ActivityLevel.MODERATE, goal=GoalMode.LOSS
    )
    maintain_kcal = tracker.get_goal_calories(profile_maintain)
    loss_kcal = tracker.get_goal_calories(profile_loss)
    assert loss_kcal == maintain_kcal - 500
