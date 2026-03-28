from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from calorie_tracker.models import (
    ActivityLevel,
    Entry,
    GoalMode,
    StorageError,
    UserProfile,
)


class StorageProtocol(Protocol):
    def save(self, entry: Entry) -> None: ...
    def load_day(self, day: date) -> list[Entry]: ...
    def delete_entry(self, day: date, index: int) -> Entry: ...


class JsonStorage:
    """Хранилище записей в JSON-файлах (по одному файлу на день)."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        if data_dir is None:
            self._data_dir = Path.home() / ".calorie_tracker"
        else:
            self._data_dir = Path(data_dir)

    def _file_path(self, day: date) -> Path:
        return self._data_dir / f"{day.isoformat()}.json"

    @property
    def _profile_path(self) -> Path:
        return self._data_dir / "profile.json"

    def save(self, entry: Entry) -> None:
        """Дописывает запись в файл YYYY-MM-DD.json; создаёт директорию при необходимости."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path = self._file_path(entry.timestamp.date())

        existing = self.load_day(entry.timestamp.date())
        existing.append(entry)

        records = [
            {
                "name": e.name,
                "calories": e.calories,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in existing
        ]

        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_day(self, day: date) -> list[Entry]:
        """Читает файл дня; при повреждённом JSON бросает StorageError."""
        path = self._file_path(day)

        if not path.exists():
            return []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StorageError(f"Повреждённый JSON-файл: {path}") from exc

        return [
            Entry(
                name=record["name"],
                calories=record["calories"],
                timestamp=datetime.fromisoformat(record["timestamp"]),
            )
            for record in data
        ]

    def delete_entry(self, day: date, index: int) -> Entry:
        """Удаляет запись по индексу из файла дня. Возвращает удалённую запись."""
        entries = self.load_day(day)
        if index < 0 or index >= len(entries):
            raise StorageError(f"Запись с индексом {index} не найдена")
        removed = entries.pop(index)
        path = self._file_path(day)
        records = [
            {"name": e.name, "calories": e.calories, "timestamp": e.timestamp.isoformat()}
            for e in entries
        ]
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return removed

    def save_profile(self, profile: UserProfile) -> None:
        """Сохраняет профиль пользователя."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "weight_kg": profile.weight_kg,
            "height_cm": profile.height_cm,
            "age": profile.age,
            "male": profile.male,
            "activity": profile.activity.value,
            "goal": profile.goal.value,
        }
        self._profile_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_profile(self) -> UserProfile | None:
        """Загружает профиль пользователя. Возвращает None если профиль не создан."""
        if not self._profile_path.exists():
            return None
        try:
            data = json.loads(self._profile_path.read_text(encoding="utf-8"))
            return UserProfile(
                weight_kg=data["weight_kg"],
                height_cm=data["height_cm"],
                age=data["age"],
                male=data["male"],
                activity=ActivityLevel(data["activity"]),
                goal=GoalMode(data["goal"]),
            )
        except (json.JSONDecodeError, KeyError) as exc:
            raise StorageError(f"Повреждённый профиль: {self._profile_path}") from exc
