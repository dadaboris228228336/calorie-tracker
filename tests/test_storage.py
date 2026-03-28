# Feature: calorie-tracker, Property 7: Round-trip хранилища

import json
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from calorie_tracker.models import Entry, StorageError
from calorie_tracker.storage import JsonStorage

# Стратегия для генерации валидных Entry (включая Unicode в названиях)
entry_strategy = st.builds(
    Entry,
    name=st.text(min_size=1).filter(lambda s: s.strip() != ""),
    calories=st.integers(min_value=1, max_value=99_999),
    timestamp=st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2099, 12, 31, 23, 59, 59),
    ),
)


# --- Unit-тесты для JsonStorage ---

# Validates: Requirements 6.2
def test_creates_directory_on_first_save():
    """Хранилище создаёт директорию при первом сохранении, если она не существует."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir) / "new_subdir" / "data"
        assert not data_dir.exists()

        storage = JsonStorage(data_dir=data_dir)
        entry = Entry(name="Тест", calories=100, timestamp=datetime(2024, 1, 15, 8, 0, 0))
        storage.save(entry)

        assert data_dir.exists()
        assert data_dir.is_dir()


# Validates: Requirements 6.1
def test_file_name_format():
    """Файл сохраняется с именем в формате YYYY-MM-DD.json."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        storage = JsonStorage(data_dir=data_dir)
        entry = Entry(name="Овсянка", calories=350, timestamp=datetime(2024, 3, 25, 8, 30, 0))
        storage.save(entry)

        expected_file = data_dir / "2024-03-25.json"
        assert expected_file.exists(), f"Ожидался файл {expected_file}"


# Validates: Requirements 6.3
def test_corrupted_json_raises_storage_error():
    """При повреждённом JSON load_day бросает StorageError и не перезаписывает файл."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        corrupted_file = data_dir / "2024-01-10.json"
        corrupted_file.write_text("{ not valid json !!!", encoding="utf-8")

        original_content = corrupted_file.read_text(encoding="utf-8")

        storage = JsonStorage(data_dir=data_dir)
        with pytest.raises(StorageError):
            storage.load_day(date(2024, 1, 10))

        # Файл не должен быть перезаписан
        assert corrupted_file.read_text(encoding="utf-8") == original_content


# Validates: Requirements 6.4
def test_utf8_unicode_name_roundtrip():
    """Unicode-символы в названии блюда сохраняются и читаются корректно (UTF-8)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        unicode_name = "寿司 🍣 Суши — Sushi"
        entry = Entry(name=unicode_name, calories=250, timestamp=datetime(2024, 6, 1, 12, 0, 0))
        storage.save(entry)

        loaded = storage.load_day(date(2024, 6, 1))
        assert len(loaded) == 1
        assert loaded[0].name == unicode_name

        # Проверяем, что файл действительно записан в UTF-8
        file_path = Path(tmp_dir) / "2024-06-01.json"
        raw = file_path.read_bytes()
        decoded = raw.decode("utf-8")
        assert unicode_name in decoded


# Validates: Requirements 6.1, 6.4, 6.5
@settings(max_examples=100)
@given(entry=entry_strategy)
def test_storage_round_trip(entry: Entry):
    """Свойство 7: save + load_day возвращает эквивалентную запись (включая Unicode)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        storage.save(entry)

        loaded = storage.load_day(entry.timestamp.date())

        assert any(
            e.name == entry.name
            and e.calories == entry.calories
            and e.timestamp == entry.timestamp
            for e in loaded
        ), f"Запись не найдена после сохранения: {entry}"


# --- Тесты для delete_entry ---

from calorie_tracker.models import StorageError


def test_delete_entry_removes_by_index():
    """delete_entry удаляет запись по индексу и возвращает её."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        day = date(2024, 5, 10)
        e1 = Entry(name="Завтрак", calories=300, timestamp=datetime(2024, 5, 10, 8, 0))
        e2 = Entry(name="Обед",    calories=600, timestamp=datetime(2024, 5, 10, 13, 0))
        e3 = Entry(name="Ужин",    calories=400, timestamp=datetime(2024, 5, 10, 19, 0))
        storage.save(e1)
        storage.save(e2)
        storage.save(e3)

        removed = storage.delete_entry(day, 1)

        assert removed.name == "Обед"
        remaining = storage.load_day(day)
        assert len(remaining) == 2
        assert all(e.name != "Обед" for e in remaining)


def test_delete_entry_invalid_index_raises():
    """delete_entry с индексом за пределами списка бросает StorageError."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        day = date(2024, 5, 10)
        storage.save(Entry(name="Завтрак", calories=300, timestamp=datetime(2024, 5, 10, 8, 0)))

        with pytest.raises(StorageError):
            storage.delete_entry(day, 99)


def test_delete_entry_negative_index_raises():
    """delete_entry с отрицательным индексом бросает StorageError."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        day = date(2024, 5, 10)
        storage.save(Entry(name="Завтрак", calories=300, timestamp=datetime(2024, 5, 10, 8, 0)))

        with pytest.raises(StorageError):
            storage.delete_entry(day, -1)


# --- Тесты для save_profile / load_profile ---

from calorie_tracker.models import ActivityLevel, GoalMode, UserProfile


def test_save_and_load_profile_roundtrip():
    """save_profile + load_profile возвращает эквивалентный профиль."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        profile = UserProfile(
            weight_kg=75.5, height_cm=178.0, age=30,
            male=True,
            activity=ActivityLevel.ACTIVE,
            goal=GoalMode.LOSS,
        )
        storage.save_profile(profile)
        loaded = storage.load_profile()

        assert loaded is not None
        assert loaded.weight_kg == profile.weight_kg
        assert loaded.height_cm == profile.height_cm
        assert loaded.age == profile.age
        assert loaded.male == profile.male
        assert loaded.activity == profile.activity
        assert loaded.goal == profile.goal


def test_load_profile_returns_none_if_not_exists():
    """load_profile возвращает None если профиль не создан."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        assert storage.load_profile() is None


def test_load_profile_corrupted_raises_storage_error():
    """load_profile бросает StorageError при повреждённом файле профиля."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        storage._data_dir.mkdir(parents=True, exist_ok=True)
        storage._profile_path.write_text("{ bad json", encoding="utf-8")

        with pytest.raises(StorageError):
            storage.load_profile()


def test_save_profile_overwrites_existing():
    """Повторный save_profile перезаписывает старый профиль."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(data_dir=Path(tmp_dir))
        p1 = UserProfile(weight_kg=80, height_cm=180, age=25, male=True,
                         activity=ActivityLevel.SEDENTARY, goal=GoalMode.MAINTAIN)
        p2 = UserProfile(weight_kg=75, height_cm=180, age=25, male=True,
                         activity=ActivityLevel.ACTIVE, goal=GoalMode.GAIN)
        storage.save_profile(p1)
        storage.save_profile(p2)
        loaded = storage.load_profile()

        assert loaded.weight_kg == 75
        assert loaded.activity == ActivityLevel.ACTIVE
        assert loaded.goal == GoalMode.GAIN
