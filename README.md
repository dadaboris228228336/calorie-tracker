# Calorie Tracker

Модульное Python-приложение для учёта калорий через командную строку.

## Установка

```bash
pip install -r requirements.txt
pip install -e .
```

## Использование

```bash
# Добавить приём пищи
calorie-tracker add "Овсянка" 350

# Статистика за сегодня
calorie-tracker stats day

# Статистика за конкретный день
calorie-tracker stats day --date 2024-03-15

# Статистика за неделю
calorie-tracker stats week

# Статистика за месяц
calorie-tracker stats month --year 2024 --month 3

# Статистика за год
calorie-tracker stats year --year 2024
```

## Запуск тестов

```bash
pytest
```

## Структура проекта

```
calorie_tracker/
├── main.py       # точка входа
├── models.py     # модели данных
├── storage.py    # хранилище (JSON-файлы)
├── tracker.py    # бизнес-логика
└── cli.py        # CLI (argparse)
tests/
├── test_storage.py
├── test_tracker.py
└── test_cli.py
```

Данные хранятся в `~/.calorie_tracker/` в формате `YYYY-MM-DD.json`.
