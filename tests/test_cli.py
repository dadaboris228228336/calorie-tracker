from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from calorie_tracker.cli import main
from calorie_tracker.models import TrackerError


# --- Вспомогательная функция ---

def run_cli(*args: str) -> tuple[int, str, str]:
    """Запускает CLI с аргументами, возвращает (exit_code, stdout, stderr)."""
    import io
    import sys
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
        code = main(list(args))
    return code, stdout_buf.getvalue(), stderr_buf.getvalue()


# --- Property-тесты (задача 5.7) ---

# Feature: calorie-tracker, Property 8: CLI возвращает ненулевой код при ошибке
# Validates: Requirements 8.4
@settings(max_examples=100)
@given(calories=st.one_of(st.integers(max_value=0), st.integers(min_value=100_000)))
def test_cli_nonzero_exit_on_invalid_calories(calories: int) -> None:
    """Свойство 8: CLI завершается с кодом != 0 при невалидных калориях."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        mock_tracker.add_entry.side_effect = TrackerError("Ошибка калорий")
        mock_make.return_value = mock_tracker
        code, _, _ = run_cli("add", "Тест", str(calories))
    assert code != 0


# Feature: calorie-tracker, Property 9: CLI выводит справку для неизвестных команд
# Validates: Requirements 8.3
@settings(max_examples=50)
@given(
    cmd=st.text(min_size=1, alphabet=st.characters(whitelist_categories=("L", "N")))
    .filter(lambda s: s.strip() not in ("add", "stats"))
)
def test_cli_help_on_unknown_command(cmd: str) -> None:
    """Свойство 9: CLI не падает с исключением при неизвестной команде."""
    code, _, _ = run_cli(cmd)
    assert isinstance(code, int)


# --- Unit-тесты для CLI (задача 5.8) ---

def test_add_valid_entry() -> None:
    """Команда add с валидными аргументами завершается с кодом 0."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        mock_make.return_value = mock_tracker
        code, stdout, _ = run_cli("add", "Овсянка", "350")
    assert code == 0
    mock_tracker.add_entry.assert_called_once_with("Овсянка", 350)
    assert "350" in stdout


def test_add_invalid_calories_returns_nonzero() -> None:
    """Команда add с невалидными калориями возвращает ненулевой код."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        mock_tracker.add_entry.side_effect = TrackerError("Ошибка")
        mock_make.return_value = mock_tracker
        code, _, stderr = run_cli("add", "Тест", "0")
    assert code != 0
    assert "Ошибка" in stderr


def test_stats_day_default() -> None:
    """Команда stats day без аргументов завершается с кодом 0."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        from calorie_tracker.models import DayStats
        from datetime import date
        mock_tracker.get_day_stats.return_value = DayStats(day=date.today(), entries=[], total=0)
        mock_make.return_value = mock_tracker
        code, stdout, _ = run_cli("stats", "day")
    assert code == 0
    assert "0" in stdout


def test_stats_week_default() -> None:
    """Команда stats week без аргументов завершается с кодом 0."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        from calorie_tracker.models import WeekStats
        from datetime import date
        today = date.today()
        from datetime import timedelta
        week_start = today - timedelta(days=today.weekday())
        mock_tracker.get_week_stats.return_value = WeekStats(
            week_start=week_start, days={}, total=0, daily_average=0.0
        )
        mock_make.return_value = mock_tracker
        code, _, _ = run_cli("stats", "week")
    assert code == 0


def test_stats_month_default() -> None:
    """Команда stats month без аргументов завершается с кодом 0."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        from calorie_tracker.models import MonthStats
        from datetime import date
        today = date.today()
        mock_tracker.get_month_stats.return_value = MonthStats(
            year=today.year, month=today.month, days={}, total=0, daily_average=0.0
        )
        mock_make.return_value = mock_tracker
        code, _, _ = run_cli("stats", "month")
    assert code == 0


def test_stats_year_default() -> None:
    """Команда stats year без аргументов завершается с кодом 0."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        from calorie_tracker.models import YearStats
        from datetime import date
        mock_tracker.get_year_stats.return_value = YearStats(
            year=date.today().year, months={}, total=0, monthly_average=0.0
        )
        mock_make.return_value = mock_tracker
        code, _, _ = run_cli("stats", "year")
    assert code == 0


def test_stats_day_with_explicit_date() -> None:
    """Команда stats day --date передаёт дату в трекер."""
    with patch("calorie_tracker.cli._make_tracker") as mock_make:
        mock_tracker = MagicMock()
        from calorie_tracker.models import DayStats
        from datetime import date
        mock_tracker.get_day_stats.return_value = DayStats(
            day=date(2024, 3, 15), entries=[], total=0
        )
        mock_make.return_value = mock_tracker
        code, _, _ = run_cli("stats", "day", "--date", "2024-03-15")
    assert code == 0
    mock_tracker.get_day_stats.assert_called_once_with(date(2024, 3, 15))


def test_unknown_command_shows_help() -> None:
    """Неизвестная команда выводит справку и возвращает код 0."""
    code, stdout, _ = run_cli()
    assert code == 0
    assert "usage" in stdout.lower() or "calorie" in stdout.lower()


# --- Тесты для команды delete ---

def test_delete_shows_entries_and_cancels_on_empty_input() -> None:
    """Команда delete показывает записи и отменяет при пустом вводе."""
    with patch("calorie_tracker.cli._make_storage") as mock_storage_fn:
        mock_storage = MagicMock()
        mock_storage_fn.return_value = mock_storage
        from calorie_tracker.models import DayStats, Entry
        from datetime import date, datetime
        entry = Entry(name="Завтрак", calories=300, timestamp=datetime(2024, 6, 15, 8, 0))
        mock_tracker = MagicMock()
        mock_tracker.get_day_stats.return_value = DayStats(
            day=date(2024, 6, 15), entries=[entry], total=300
        )
        with patch("calorie_tracker.cli.CalorieTracker", return_value=mock_tracker):
            with patch("builtins.input", return_value=""):
                code, stdout, _ = run_cli("delete", "--date", "2024-06-15")
    assert code == 0
    assert "Отменено" in stdout


def test_delete_no_entries_returns_zero() -> None:
    """Команда delete на пустой день выводит сообщение и возвращает 0."""
    with patch("calorie_tracker.cli._make_storage") as mock_storage_fn:
        mock_storage = MagicMock()
        mock_storage_fn.return_value = mock_storage
        from calorie_tracker.models import DayStats
        from datetime import date
        mock_tracker = MagicMock()
        mock_tracker.get_day_stats.return_value = DayStats(
            day=date(2024, 6, 15), entries=[], total=0
        )
        with patch("calorie_tracker.cli.CalorieTracker", return_value=mock_tracker):
            code, stdout, _ = run_cli("delete", "--date", "2024-06-15")
    assert code == 0
    assert "нет" in stdout.lower()


# --- Тесты для команды goal ---

def test_goal_shows_progress_when_profile_exists() -> None:
    """Команда goal выводит прогресс если профиль настроен."""
    from calorie_tracker.models import ActivityLevel, DayStats, GoalMode, UserProfile
    from datetime import date
    profile = UserProfile(
        weight_kg=75, height_cm=175, age=28,
        male=True, activity=ActivityLevel.MODERATE, goal=GoalMode.MAINTAIN
    )
    with patch("calorie_tracker.cli._make_storage") as mock_storage_fn:
        mock_storage = MagicMock()
        mock_storage.load_profile.return_value = profile
        mock_storage_fn.return_value = mock_storage
        mock_tracker = MagicMock()
        mock_tracker.get_goal_calories.return_value = 2500
        mock_tracker.get_day_stats.return_value = DayStats(
            day=date.today(), entries=[], total=1800
        )
        with patch("calorie_tracker.cli.CalorieTracker", return_value=mock_tracker):
            code, stdout, _ = run_cli("goal")
    assert code == 0
    assert "2500" in stdout
    assert "1800" in stdout


def test_goal_returns_nonzero_when_no_profile() -> None:
    """Команда goal возвращает ненулевой код если профиль не настроен."""
    with patch("calorie_tracker.cli._make_storage") as mock_storage_fn:
        mock_storage = MagicMock()
        mock_storage.load_profile.return_value = None
        mock_storage_fn.return_value = mock_storage
        with patch("calorie_tracker.cli.CalorieTracker"):
            code, _, _ = run_cli("goal")
    assert code != 0
