from __future__ import annotations

import sys
from datetime import date

from calorie_tracker.models import (
    ActivityLevel,
    GoalMode,
    StorageError,
    TrackerError,
    UserProfile,
)
from calorie_tracker.storage import JsonStorage
from calorie_tracker.tracker import CalorieTracker


def _make_storage() -> JsonStorage:
    return JsonStorage()


def _make_tracker() -> CalorieTracker:
    return CalorieTracker(_make_storage())


# ── add ──────────────────────────────────────────────────────────────────────

def _cmd_add(args) -> int:
    tracker = _make_tracker()
    try:
        tracker.add_entry(args.name, args.calories)
        print(f"Добавлено: {args.name} — {args.calories} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


# ── delete ───────────────────────────────────────────────────────────────────

def _cmd_delete(args) -> int:
    storage = _make_storage()
    tracker = CalorieTracker(storage)
    try:
        day = date.fromisoformat(args.date) if args.date else date.today()
        stats = tracker.get_day_stats(day)
        if not stats.entries:
            print("Записей за этот день нет.")
            return 0
        print(f"\nЗаписи за {day}:")
        for i, e in enumerate(stats.entries):
            print(f"  [{i}]  {e.timestamp.strftime('%H:%M')}  {e.name}: {e.calories} ккал")
        print()
        raw = input("Введите номер записи для удаления (или Enter для отмены): ").strip()
        if not raw:
            print("Отменено.")
            return 0
        idx = int(raw)
        removed = tracker.delete_entry(day, idx)
        print(f"Удалено: {removed.name} — {removed.calories} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1
    except ValueError:
        print("Ошибка: введите корректный номер.", file=sys.stderr)
        return 1


# ── photo ─────────────────────────────────────────────────────────────────────

def _cmd_photo(args) -> int:
    from calorie_tracker.vision import recognize_food
    tracker = _make_tracker()
    try:
        print(f"Анализирую фото: {args.image} ...")
        items = recognize_food(args.image)
        if not items:
            print("Еда на фото не распознана.")
            return 0
        print("\nРаспознано:")
        for i, item in enumerate(items):
            print(f"  [{i}]  {item['name']}: {item['calories']} ккал")
        print()
        raw = input("Введите номера для добавления через запятую (или Enter — добавить все): ").strip()
        if raw:
            indices = [int(x.strip()) for x in raw.split(",")]
            selected = [items[i] for i in indices if 0 <= i < len(items)]
        else:
            selected = items
        for item in selected:
            tracker.add_entry(item["name"], item["calories"])
            print(f"  ✓ Добавлено: {item['name']} — {item['calories']} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1
    except (ValueError, IndexError):
        print("Ошибка: некорректный ввод номеров.", file=sys.stderr)
        return 1


# ── profile ───────────────────────────────────────────────────────────────────

_ACTIVITY_LABELS = {
    "1": (ActivityLevel.SEDENTARY,   "Сидячий образ жизни"),
    "2": (ActivityLevel.LIGHT,       "Лёгкая активность (1–3 дня/нед)"),
    "3": (ActivityLevel.MODERATE,    "Умеренная активность (3–5 дней/нед)"),
    "4": (ActivityLevel.ACTIVE,      "Высокая активность (6–7 дней/нед)"),
    "5": (ActivityLevel.VERY_ACTIVE, "Очень высокая / спортсмен"),
}

_GOAL_LABELS = {
    "1": (GoalMode.LOSS,     "Похудение (дефицит −500 ккал/день)"),
    "2": (GoalMode.MAINTAIN, "Поддержание веса"),
    "3": (GoalMode.GAIN,     "Набор массы (профицит +400 ккал/день)"),
}


def _cmd_profile(args) -> int:
    storage = _make_storage()
    tracker = CalorieTracker(storage)
    try:
        print("\n── Настройка профиля ──────────────────────")
        weight = float(input("  Вес (кг): "))
        height = float(input("  Рост (см): "))
        age    = int(input("  Возраст: "))
        sex    = input("  Пол (м/ж): ").strip().lower()
        male   = sex in ("м", "m", "мужской", "male")

        print("\n  Уровень активности:")
        for k, (_, label) in _ACTIVITY_LABELS.items():
            print(f"    [{k}] {label}")
        act_key = input("  Выбор [1–5]: ").strip()
        activity = _ACTIVITY_LABELS.get(act_key, _ACTIVITY_LABELS["3"])[0]

        print("\n  Цель:")
        for k, (_, label) in _GOAL_LABELS.items():
            print(f"    [{k}] {label}")
        goal_key = input("  Выбор [1–3]: ").strip()
        goal = _GOAL_LABELS.get(goal_key, _GOAL_LABELS["2"])[0]

        profile = UserProfile(
            weight_kg=weight, height_cm=height, age=age,
            male=male, activity=activity, goal=goal,
        )
        storage.save_profile(profile)

        goal_kcal = tracker.get_goal_calories(profile)
        goal_name = {GoalMode.LOSS: "Похудение", GoalMode.MAINTAIN: "Поддержание", GoalMode.GAIN: "Набор массы"}[goal]
        print(f"\n  ✓ Профиль сохранён.")
        print(f"  Цель: {goal_name}")
        print(f"  Целевые калории в день: {goal_kcal} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1
    except ValueError:
        print("Ошибка: некорректный ввод.", file=sys.stderr)
        return 1


def _cmd_goal(args) -> int:
    """Показывает текущую цель и прогресс за сегодня."""
    storage = _make_storage()
    tracker = CalorieTracker(storage)
    try:
        profile = storage.load_profile()
        if profile is None:
            print("Профиль не настроен. Используйте команду 'profile'.")
            return 1
        goal_kcal = tracker.get_goal_calories(profile)
        stats = tracker.get_day_stats()
        eaten = stats.total
        remaining = goal_kcal - eaten
        goal_name = {GoalMode.LOSS: "Похудение", GoalMode.MAINTAIN: "Поддержание", GoalMode.GAIN: "Набор массы"}[profile.goal]
        print(f"\n  Режим: {goal_name}")
        print(f"  Цель:     {goal_kcal} ккал/день")
        print(f"  Съедено:  {eaten} ккал")
        if remaining >= 0:
            print(f"  Осталось: {remaining} ккал")
        else:
            print(f"  Превышение: {abs(remaining)} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


# ── stats ─────────────────────────────────────────────────────────────────────

def _cmd_stats_day(args) -> int:
    tracker = _make_tracker()
    try:
        day = date.fromisoformat(args.date) if args.date else None
        stats = tracker.get_day_stats(day)
        if not stats.entries:
            print("Записей за указанный день не найдено")
        else:
            for e in stats.entries:
                print(f"  {e.timestamp.strftime('%H:%M')}  {e.name}: {e.calories} ккал")
        print(f"Итого: {stats.total} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


def _cmd_stats_week(args) -> int:
    tracker = _make_tracker()
    try:
        week_date = date.fromisoformat(args.date) if args.date else None
        stats = tracker.get_week_stats(week_date)
        if stats.total == 0:
            print("Записей за указанную неделю не найдено")
        else:
            for d, cal in stats.days.items():
                print(f"  {d.strftime('%a %d.%m')}: {cal} ккал")
        print(f"Итого: {stats.total} ккал  |  Среднее в день: {stats.daily_average:.1f} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


def _cmd_stats_month(args) -> int:
    tracker = _make_tracker()
    try:
        stats = tracker.get_month_stats(args.year, args.month)
        if stats.total == 0:
            print("Записей за указанный месяц не найдено")
        else:
            for d, cal in stats.days.items():
                if cal > 0:
                    print(f"  {d.strftime('%d.%m')}: {cal} ккал")
        print(f"Итого: {stats.total} ккал  |  Среднее в день: {stats.daily_average:.1f} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


def _cmd_stats_year(args) -> int:
    tracker = _make_tracker()
    try:
        stats = tracker.get_year_stats(args.year)
        months_ru = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                     "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        if stats.total == 0:
            print("Записей за указанный год не найдено")
        else:
            for m, cal in stats.months.items():
                if cal > 0:
                    print(f"  {months_ru[m - 1]}: {cal} ккал")
        print(f"Итого: {stats.total} ккал  |  Среднее в месяц: {stats.monthly_average:.1f} ккал")
        return 0
    except (TrackerError, StorageError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


# ── parser ────────────────────────────────────────────────────────────────────

def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="calorie-tracker",
        description="Трекер калорий — учёт питания через командную строку",
    )
    subparsers = parser.add_subparsers(dest="command")

    # add
    add_p = subparsers.add_parser("add", help="Добавить приём пищи")
    add_p.add_argument("name", type=str, help="Название блюда")
    add_p.add_argument("calories", type=int, help="Количество калорий")

    # delete
    del_p = subparsers.add_parser("delete", help="Удалить запись")
    del_p.add_argument("--date", type=str, default=None, metavar="YYYY-MM-DD")

    # photo
    photo_p = subparsers.add_parser("photo", help="Распознать еду по фото (Ollama LLaVA)")
    photo_p.add_argument("image", type=str, help="Путь к фото")

    # profile
    subparsers.add_parser("profile", help="Настроить профиль и цель")

    # goal
    subparsers.add_parser("goal", help="Показать цель и прогресс за сегодня")

    # stats
    stats_p = subparsers.add_parser("stats", help="Просмотр статистики")
    stats_sub = stats_p.add_subparsers(dest="period")

    day_p = stats_sub.add_parser("day", help="Статистика за день")
    day_p.add_argument("--date", type=str, default=None, metavar="YYYY-MM-DD")

    week_p = stats_sub.add_parser("week", help="Статистика за неделю")
    week_p.add_argument("--date", type=str, default=None, metavar="YYYY-MM-DD")

    month_p = stats_sub.add_parser("month", help="Статистика за месяц")
    month_p.add_argument("--year", type=int, default=None)
    month_p.add_argument("--month", type=int, default=None)

    year_p = stats_sub.add_parser("year", help="Статистика за год")
    year_p.add_argument("--year", type=int, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1

    if args.command == "add":
        return _cmd_add(args)
    elif args.command == "delete":
        return _cmd_delete(args)
    elif args.command == "photo":
        return _cmd_photo(args)
    elif args.command == "profile":
        return _cmd_profile(args)
    elif args.command == "goal":
        return _cmd_goal(args)
    elif args.command == "stats":
        if args.period == "day":
            return _cmd_stats_day(args)
        elif args.period == "week":
            return _cmd_stats_week(args)
        elif args.period == "month":
            return _cmd_stats_month(args)
        elif args.period == "year":
            return _cmd_stats_year(args)
        else:
            parser.print_help()
            return 0
    else:
        parser.print_help()
        return 0
