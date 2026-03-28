@echo off
chcp 65001 >nul

echo Проверка зависимостей...
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo Устанавливаю зависимости...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Ошибка установки зависимостей.
        pause
        exit /b 1
    )
    echo Зависимости установлены.
)

python main.py
