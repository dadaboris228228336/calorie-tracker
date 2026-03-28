"""Установщик зависимостей с графическим интерфейсом (tkinter — встроен в Python)."""
import subprocess
import sys
import importlib
import os
from pathlib import Path

# Зависимости: (import_name, pip_name, отображаемое_имя)
DEPS = [
    ("PyQt6",      "PyQt6>=6.4.0",    "PyQt6  (GUI)"),
    ("pytest",     "pytest>=7.0",     "pytest  (тесты)"),
    ("hypothesis", "hypothesis>=6.0", "hypothesis  (тесты)"),
]


def is_installed(import_name: str) -> bool:
    """Проверяет установлен ли пакет корректно."""
    try:
        if import_name == "PyQt6":
            importlib.import_module("PyQt6.QtCore")
        else:
            importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def get_missing() -> list[tuple[str, str, str]]:
    """Возвращает список незаустановленных зависимостей."""
    return [(imp, pip, name) for imp, pip, name in DEPS if not is_installed(imp)]


def kill_existing() -> bool:
    """Завершает уже запущенный экземпляр приложения. Возвращает True если был найден."""
    try:
        import psutil
    except ImportError:
        # psutil не установлен — пробуем через taskkill
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "pythonw.exe", "/FI", "WINDOWTITLE eq *Calorie*"],
            capture_output=True
        )
        return result.returncode == 0

    killed = False
    current_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid == current_pid:
                continue
            cmdline = proc.info.get("cmdline") or []
            # Ищем процессы python/pythonw которые запускают main.py или installer.py
            if any("main.py" in arg for arg in cmdline):
                proc.terminate()
                proc.wait(timeout=3)
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass
    return killed


def launch_app():
    """Запускает основное приложение."""
    subprocess.Popen([sys.executable.replace("python.exe", "pythonw.exe"), "main.py"])
    sys.exit(0)


# Если приложение уже запущено — закрываем его
kill_existing()

# Если всё установлено — сразу запускаем приложение
missing = get_missing()
if not missing:
    launch_app()

# Иначе показываем окно установки
import tkinter as tk
from tkinter import ttk


class InstallerWindow:
    def __init__(self, missing: list[tuple[str, str, str]]):
        self.missing = missing
        self.root = tk.Tk()
        self.root.title("Calorie Tracker — Установка")
        self.root.geometry("480x320")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self._build_ui()

    def _build_ui(self):
        # Заголовок
        tk.Label(
            self.root, text="🥗 Calorie Tracker",
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 4))

        tk.Label(
            self.root, text="Необходимо установить зависимости",
            bg="#1e1e2e", fg="#6c7086",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 16))

        # Текущий пакет
        tk.Label(
            self.root, text="Текущий пакет:",
            bg="#1e1e2e", fg="#6c7086",
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=30)

        self.current_lbl = tk.Label(
            self.root, text="",
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Segoe UI", 10, "bold")
        )
        self.current_lbl.pack(anchor="w", padx=30)

        # Прогресс текущего пакета
        self.pkg_bar = ttk.Progressbar(
            self.root, mode="indeterminate", length=420
        )
        self.pkg_bar.pack(padx=30, pady=(4, 16))

        # Общий прогресс
        tk.Label(
            self.root, text="Общий прогресс:",
            bg="#1e1e2e", fg="#6c7086",
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=30)

        self.total_bar = ttk.Progressbar(
            self.root, mode="determinate",
            length=420, maximum=len(self.missing)
        )
        self.total_bar.pack(padx=30, pady=(4, 0))

        self.total_lbl = tk.Label(
            self.root, text=f"0 / {len(self.missing)}",
            bg="#1e1e2e", fg="#6c7086",
            font=("Segoe UI", 9)
        )
        self.total_lbl.pack(pady=(4, 16))

        # Кнопка
        self.btn = tk.Button(
            self.root, text="Установить и запустить",
            bg="#7c6af7", fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=20, pady=8,
            cursor="hand2",
            command=self._start_install
        )
        self.btn.pack()

    def _start_install(self):
        """Запускает установку в фоне через after() чтобы не блокировать UI."""
        self.btn.config(state="disabled", text="Устанавливаю...")
        self._install_next(0)

    def _install_next(self, idx: int):
        """Устанавливает пакеты по одному, обновляя прогресс-бары."""
        if idx >= len(self.missing):
            # Всё установлено
            self.current_lbl.config(text="✓ Готово!", fg="#50fa7b")
            self.pkg_bar.stop()
            self.pkg_bar.config(mode="determinate", value=100, maximum=100)
            self.root.after(800, self._finish)
            return

        imp, pip, name = self.missing[idx]
        self.current_lbl.config(text=name, fg="#cdd6f4")
        self.total_lbl.config(text=f"{idx} / {len(self.missing)}")
        self.total_bar.config(value=idx)
        self.pkg_bar.start(12)  # анимация пока идёт установка
        self.root.update()

        # Запускаем pip install
        subprocess.run(
            [sys.executable, "-m", "pip", "install", pip, "--quiet"],
            capture_output=True
        )

        self.pkg_bar.stop()
        self.total_bar.config(value=idx + 1)
        self.total_lbl.config(text=f"{idx + 1} / {len(self.missing)}")
        self.root.after(200, lambda: self._install_next(idx + 1))

    def _finish(self):
        """Закрывает окно установщика и запускает приложение."""
        self.root.destroy()
        launch_app()

    def run(self):
        self.root.mainloop()


InstallerWindow(missing).run()
