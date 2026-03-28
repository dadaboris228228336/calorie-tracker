"""GUI-интерфейс Calorie Tracker на PyQt6."""
from __future__ import annotations

import sys
from datetime import date, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget,
    QDoubleSpinBox, QRadioButton, QProgressBar,
    QFileDialog,
)

from calorie_tracker.models import (
    ActivityLevel, GoalMode, StorageError, TrackerError, UserProfile,
)
from calorie_tracker.storage import JsonStorage
from calorie_tracker.tracker import CalorieTracker

# ── Цветовая палитра ──────────────────────────────────────────────────────────
DARK_BG      = "#1e1e2e"
PANEL_BG     = "#2a2a3e"
CARD_BG      = "#313145"
ACCENT       = "#7c6af7"
ACCENT_HOVER = "#9d8fff"
SUCCESS      = "#50fa7b"
WARNING      = "#ffb86c"
DANGER       = "#ff5555"
TEXT_PRIMARY = "#cdd6f4"
TEXT_MUTED   = "#6c7086"
BORDER       = "#45475a"

STYLE = f"""
QMainWindow, QDialog {{
    background-color: {DARK_BG};
}}
QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QPushButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:pressed {{
    background-color: #5a4fd4;
}}
QPushButton#danger {{
    background-color: {DANGER};
}}
QPushButton#danger:hover {{
    background-color: #ff7777;
}}
QPushButton#secondary {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
QPushButton#secondary:hover {{
    background-color: {PANEL_BG};
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QListWidget {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px;
    border-radius: 6px;
    margin: 2px;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {PANEL_BG};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {PANEL_BG};
}}
QTabBar::tab {{
    background-color: {CARD_BG};
    color: {TEXT_MUTED};
    padding: 8px 20px;
    border-radius: 6px;
    margin: 2px;
}}
QTabBar::tab:selected {{
    background-color: {ACCENT};
    color: white;
}}
QLabel#title {{
    font-size: 22px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel#subtitle {{
    font-size: 14px;
    color: {TEXT_MUTED};
}}
QLabel#card_title {{
    font-size: 13px;
    font-weight: bold;
    color: {TEXT_MUTED};
    text-transform: uppercase;
}}
QLabel#value {{
    font-size: 28px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QProgressBar {{
    background-color: {CARD_BG};
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 6px;
}}
QFrame#card {{
    background-color: {CARD_BG};
    border-radius: 12px;
    border: 1px solid {BORDER};
}}
QScrollArea {{
    border: none;
}}
"""


# ── Вспомогательные виджеты ───────────────────────────────────────────────────

def card(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("card")
    return f


def label(text: str, kind: str = "", parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    if kind:
        lbl.setObjectName(kind)
    return lbl


def hline(parent=None) -> QFrame:
    line = QFrame(parent)
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {BORDER};")
    return line


# ── Диалог добавления блюда ───────────────────────────────────────────────────

class AddEntryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить приём пищи")
        self.setMinimumWidth(360)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(label("🍽️  Добавить приём пищи", "title"))
        layout.addWidget(hline())

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Овсянка с молоком")
        form.addRow("Название блюда:", self.name_edit)

        self.cal_spin = QSpinBox()
        self.cal_spin.setRange(1, 99999)
        self.cal_spin.setValue(300)
        self.cal_spin.setSuffix(" ккал")
        form.addRow("Калории:", self.cal_spin)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_values(self) -> tuple[str, int]:
        return self.name_edit.text().strip(), self.cal_spin.value()


# ── Диалог настройки профиля ──────────────────────────────────────────────────

class ProfileDialog(QDialog):
    def __init__(self, profile: UserProfile | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка профиля")
        self.setMinimumWidth(400)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(label("👤  Профиль пользователя", "title"))
        layout.addWidget(label("Данные используются для расчёта нормы калорий", "subtitle"))
        layout.addWidget(hline())

        form = QFormLayout()
        form.setSpacing(10)

        self.weight = QDoubleSpinBox()
        self.weight.setRange(30, 300)
        self.weight.setSuffix(" кг")
        self.weight.setValue(profile.weight_kg if profile else 70)
        form.addRow("Вес:", self.weight)

        self.height = QDoubleSpinBox()
        self.height.setRange(100, 250)
        self.height.setSuffix(" см")
        self.height.setValue(profile.height_cm if profile else 170)
        form.addRow("Рост:", self.height)

        self.age = QSpinBox()
        self.age.setRange(10, 100)
        self.age.setValue(profile.age if profile else 25)
        form.addRow("Возраст:", self.age)

        sex_layout = QHBoxLayout()
        self.male_btn = QRadioButton("Мужской")
        self.female_btn = QRadioButton("Женский")
        self.male_btn.setChecked(profile.male if profile else True)
        self.female_btn.setChecked(not profile.male if profile else False)
        sex_layout.addWidget(self.male_btn)
        sex_layout.addWidget(self.female_btn)
        form.addRow("Пол:", sex_layout)

        self.activity = QComboBox()
        activities = [
            ("Сидячий образ жизни",          ActivityLevel.SEDENTARY),
            ("Лёгкая активность (1–3 дня)",   ActivityLevel.LIGHT),
            ("Умеренная активность (3–5 дней)", ActivityLevel.MODERATE),
            ("Высокая активность (6–7 дней)", ActivityLevel.ACTIVE),
            ("Очень высокая / спортсмен",     ActivityLevel.VERY_ACTIVE),
        ]
        for text, val in activities:
            self.activity.addItem(text, val)
        if profile:
            idx = [v for _, v in activities].index(profile.activity)
            self.activity.setCurrentIndex(idx)
        else:
            self.activity.setCurrentIndex(2)
        form.addRow("Активность:", self.activity)

        self.goal = QComboBox()
        goals = [
            ("🔥 Похудение (−500 ккал/день)",  GoalMode.LOSS),
            ("⚖️  Поддержание веса",            GoalMode.MAINTAIN),
            ("💪 Набор массы (+400 ккал/день)", GoalMode.GAIN),
        ]
        for text, val in goals:
            self.goal.addItem(text, val)
        if profile:
            idx = [v for _, v in goals].index(profile.goal)
            self.goal.setCurrentIndex(idx)
        else:
            self.goal.setCurrentIndex(1)
        form.addRow("Цель:", self.goal)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_profile(self) -> UserProfile:
        return UserProfile(
            weight_kg=self.weight.value(),
            height_cm=self.height.value(),
            age=self.age.value(),
            male=self.male_btn.isChecked(),
            activity=self.activity.currentData(),
            goal=self.goal.currentData(),
        )


# ── Вкладка "Сегодня" ─────────────────────────────────────────────────────────

class TodayTab(QWidget):
    def __init__(self, storage: JsonStorage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        # Заголовок + кнопки
        top = QHBoxLayout()
        top.addWidget(label(f"📅  {date.today().strftime('%d %B %Y')}", "title"))
        top.addStretch()
        add_btn = QPushButton("＋ Добавить")
        add_btn.clicked.connect(self._add_entry)
        del_btn = QPushButton("🗑 Удалить")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_entry)
        top.addWidget(add_btn)
        top.addWidget(del_btn)
        root.addLayout(top)

        # Карточки статистики
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self._total_card = self._stat_card("Съедено", "0 ккал", "🔥")
        self._goal_card  = self._stat_card("Цель", "— ккал", "🎯")
        self._left_card  = self._stat_card("Осталось", "— ккал", "✅")
        cards_row.addWidget(self._total_card[0])
        cards_row.addWidget(self._goal_card[0])
        cards_row.addWidget(self._left_card[0])
        root.addLayout(cards_row)

        # Прогресс-бар
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        self._progress.setFixedHeight(14)
        root.addWidget(self._progress)

        # Список записей
        root.addWidget(label("Приёмы пищи", "card_title"))
        self._list = QListWidget()
        self._list.setAlternatingRowColors(False)
        root.addWidget(self._list)

    def _stat_card(self, title: str, value: str, icon: str):
        f = card()
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        lbl_title = label(f"{icon}  {title}", "card_title")
        lbl_val   = label(value, "value")
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_val)
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return f, lbl_val

    def refresh(self):
        stats = self._tracker.get_day_stats()
        profile = self._storage.load_profile()

        # Обновляем карточки
        self._total_card[1].setText(f"{stats.total} ккал")

        if profile:
            goal_kcal = self._tracker.get_goal_calories(profile)
            remaining = goal_kcal - stats.total
            self._goal_card[1].setText(f"{goal_kcal} ккал")
            if remaining >= 0:
                self._left_card[1].setText(f"{remaining} ккал")
                self._left_card[1].setStyleSheet(f"color: {SUCCESS}; font-size: 28px; font-weight: bold;")
            else:
                self._left_card[1].setText(f"−{abs(remaining)} ккал")
                self._left_card[1].setStyleSheet(f"color: {DANGER}; font-size: 28px; font-weight: bold;")
            pct = min(100, int(100 * stats.total / goal_kcal)) if goal_kcal > 0 else 0
            self._progress.setValue(pct)
            color = SUCCESS if pct <= 100 else DANGER
            self._progress.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {color}; border-radius: 6px; }}"
            )
        else:
            self._goal_card[1].setText("Нет профиля")
            self._left_card[1].setText("—")
            self._progress.setValue(0)

        # Список
        self._list.clear()
        if not stats.entries:
            item = QListWidgetItem("  Записей нет. Нажмите «＋ Добавить»")
            item.setForeground(QColor(TEXT_MUTED))
            self._list.addItem(item)
        else:
            for e in stats.entries:
                item = QListWidgetItem(
                    f"  {e.timestamp.strftime('%H:%M')}   {e.name}   —   {e.calories} ккал"
                )
                self._list.addItem(item)

    def _add_entry(self):
        dlg = AddEntryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, cal = dlg.get_values()
            try:
                self._tracker.add_entry(name, cal)
                self.refresh()
            except TrackerError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _delete_entry(self):
        row = self._list.currentRow()
        stats = self._tracker.get_day_stats()
        if not stats.entries:
            QMessageBox.information(self, "Удаление", "Нет записей для удаления.")
            return
        if row < 0:
            QMessageBox.information(self, "Удаление", "Выберите запись для удаления.")
            return
        entry = stats.entries[row]
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить «{entry.name}» ({entry.calories} ккал)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._tracker.delete_entry(date.today(), row)
                self.refresh()
            except StorageError as e:
                QMessageBox.warning(self, "Ошибка", str(e))


# ── Вкладка "Статистика" ──────────────────────────────────────────────────────

class StatsTab(QWidget):
    def __init__(self, storage: JsonStorage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("📊  Статистика", "title"))

        # Переключатель периода
        period_row = QHBoxLayout()
        self._period_btns: list[QPushButton] = []
        for text, period in [("Неделя", "week"), ("Месяц", "month"), ("Год", "year")]:
            btn = QPushButton(text)
            btn.setObjectName("secondary")
            btn.setProperty("period", period)
            btn.clicked.connect(lambda _, p=period: self._show_period(p))
            self._period_btns.append(btn)
            period_row.addWidget(btn)
        period_row.addStretch()
        root.addLayout(period_row)

        # Область с результатами
        self._result_list = QListWidget()
        root.addWidget(self._result_list)

        # Итого
        self._total_lbl = label("", "subtitle")
        root.addWidget(self._total_lbl)

        self._show_period("week")

    def _show_period(self, period: str):
        self._result_list.clear()
        try:
            if period == "week":
                stats = self._tracker.get_week_stats()
                days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                for d, cal in stats.days.items():
                    wd = days_ru[d.weekday()]
                    item = QListWidgetItem(f"  {wd}  {d.strftime('%d.%m')}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                self._total_lbl.setText(
                    f"Итого: {stats.total} ккал  |  Среднее: {stats.daily_average:.0f} ккал/день"
                )

            elif period == "month":
                stats = self._tracker.get_month_stats()
                for d, cal in stats.days.items():
                    item = QListWidgetItem(f"  {d.strftime('%d %b')}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                self._total_lbl.setText(
                    f"Итого: {stats.total} ккал  |  Среднее: {stats.daily_average:.0f} ккал/день"
                )

            elif period == "year":
                stats = self._tracker.get_year_stats()
                months_ru = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                             "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
                for m, cal in stats.months.items():
                    item = QListWidgetItem(f"  {months_ru[m-1]}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                self._total_lbl.setText(
                    f"Итого: {stats.total} ккал  |  Среднее: {stats.monthly_average:.0f} ккал/месяц"
                )
        except StorageError as e:
            QMessageBox.warning(self, "Ошибка", str(e))


# ── Вкладка "Фото AI" ─────────────────────────────────────────────────────────

class PhotoTab(QWidget):
    def __init__(self, storage: JsonStorage, today_tab: "TodayTab", parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)
        self._today_tab = today_tab
        self._items: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("📷  Распознать еду по фото", "title"))
        root.addWidget(label("Используется локальная модель Ollama LLaVA", "subtitle"))
        root.addWidget(hline())

        # Выбор файла
        file_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Путь к фото...")
        self._path_edit.setReadOnly(True)
        browse_btn = QPushButton("📂 Выбрать фото")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(self._path_edit)
        file_row.addWidget(browse_btn)
        root.addLayout(file_row)

        analyze_btn = QPushButton("🔍 Анализировать")
        analyze_btn.clicked.connect(self._analyze)
        root.addWidget(analyze_btn)

        self._status_lbl = label("", "subtitle")
        root.addWidget(self._status_lbl)

        root.addWidget(label("Распознанные блюда:", "card_title"))
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        root.addWidget(self._list)

        add_btn = QPushButton("✓ Добавить выбранные")
        add_btn.clicked.connect(self._add_selected)
        root.addWidget(add_btn)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите фото", "",
            "Изображения (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if path:
            self._path_edit.setText(path)

    def _analyze(self):
        path = self._path_edit.text()
        if not path:
            QMessageBox.warning(self, "Ошибка", "Выберите фото.")
            return
        self._status_lbl.setText("⏳ Анализирую...")
        self._list.clear()
        self._items = []
        QApplication.processEvents()
        try:
            from calorie_tracker.vision import recognize_food
            items = recognize_food(path)
            self._items = items
            if not items:
                self._status_lbl.setText("Еда не распознана.")
            else:
                self._status_lbl.setText(f"Найдено блюд: {len(items)}. Выберите нужные и нажмите «Добавить».")
                for item in items:
                    self._list.addItem(f"  {item['name']}  —  {item['calories']} ккал")
                self._list.selectAll()
        except TrackerError as e:
            self._status_lbl.setText(f"Ошибка: {e}")

    def _add_selected(self):
        selected = [self._list.row(i) for i in self._list.selectedItems()]
        if not selected:
            QMessageBox.information(self, "Добавление", "Ничего не выбрано.")
            return
        added = 0
        for idx in selected:
            item = self._items[idx]
            try:
                self._tracker.add_entry(item["name"], item["calories"])
                added += 1
            except TrackerError as e:
                QMessageBox.warning(self, "Ошибка", str(e))
        if added:
            self._today_tab.refresh()
            QMessageBox.information(self, "Готово", f"Добавлено блюд: {added}")


# ── Вкладка "Профиль" ─────────────────────────────────────────────────────────

class ProfileTab(QWidget):
    def __init__(self, storage: JsonStorage, today_tab: "TodayTab", parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)
        self._today_tab = today_tab
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("👤  Профиль и цель", "title"))
        root.addWidget(hline())

        self._info_card = card()
        self._info_layout = QVBoxLayout(self._info_card)
        self._info_layout.setContentsMargins(16, 12, 16, 12)
        root.addWidget(self._info_card)

        edit_btn = QPushButton("✏️  Редактировать профиль")
        edit_btn.clicked.connect(self._edit_profile)
        root.addWidget(edit_btn)
        root.addStretch()

    def refresh(self):
        # Очищаем карточку
        while self._info_layout.count():
            child = self._info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        profile = self._storage.load_profile()
        if not profile:
            self._info_layout.addWidget(label("Профиль не настроен.", "subtitle"))
            self._info_layout.addWidget(label("Нажмите «Редактировать профиль» для настройки.", "subtitle"))
            return

        goal_kcal = self._tracker.get_goal_calories(profile)
        goal_names = {GoalMode.LOSS: "🔥 Похудение", GoalMode.MAINTAIN: "⚖️ Поддержание", GoalMode.GAIN: "💪 Набор массы"}
        act_names = {
            ActivityLevel.SEDENTARY: "Сидячий",
            ActivityLevel.LIGHT: "Лёгкая",
            ActivityLevel.MODERATE: "Умеренная",
            ActivityLevel.ACTIVE: "Высокая",
            ActivityLevel.VERY_ACTIVE: "Очень высокая",
        }
        sex = "Мужской" if profile.male else "Женский"

        rows = [
            ("Вес",        f"{profile.weight_kg} кг"),
            ("Рост",       f"{profile.height_cm} см"),
            ("Возраст",    f"{profile.age} лет"),
            ("Пол",        sex),
            ("Активность", act_names[profile.activity]),
            ("Цель",       goal_names[profile.goal]),
            ("Норма калорий", f"{goal_kcal} ккал/день"),
        ]
        for title, val in rows:
            row_w = QHBoxLayout()
            row_w.addWidget(label(title, "card_title"))
            row_w.addStretch()
            row_w.addWidget(label(val))
            self._info_layout.addLayout(row_w)
            self._info_layout.addWidget(hline())

    def _edit_profile(self):
        profile = self._storage.load_profile()
        dlg = ProfileDialog(profile, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_profile = dlg.get_profile()
            try:
                self._storage.save_profile(new_profile)
                self.refresh()
                self._today_tab.refresh()
            except StorageError as e:
                QMessageBox.warning(self, "Ошибка", str(e))


# ── Главное окно ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🥗 Calorie Tracker")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(STYLE)

        self._storage = JsonStorage()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Шапка
        header = QWidget()
        header.setStyleSheet(f"background-color: {PANEL_BG}; border-bottom: 1px solid {BORDER};")
        header.setFixedHeight(56)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        title_lbl = label("🥗  Calorie Tracker", "title")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY};")
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()
        root.addWidget(header)

        # Вкладки
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        self._today_tab = TodayTab(self._storage)
        self._stats_tab = StatsTab(self._storage)
        self._photo_tab = PhotoTab(self._storage, self._today_tab)
        self._profile_tab = ProfileTab(self._storage, self._today_tab)

        tabs.addTab(self._today_tab,   "📅  Сегодня")
        tabs.addTab(self._stats_tab,   "📊  Статистика")
        tabs.addTab(self._photo_tab,   "📷  Фото AI")
        tabs.addTab(self._profile_tab, "👤  Профиль")

        tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(tabs)

    def _on_tab_changed(self, idx: int):
        if idx == 0:
            self._today_tab.refresh()
        elif idx == 1:
            self._stats_tab._show_period("week")
        elif idx == 3:
            self._profile_tab.refresh()


# ── Точка входа ───────────────────────────────────────────────────────────────

def run_app() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


# ── Вкладка "Сегодня" ─────────────────────────────────────────────────────────

class TodayTab(QWidget):
    """Вкладка с записями за сегодня, карточками статистики и прогресс-баром."""

    def __init__(self, storage: JsonStorage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)  # трекер для бизнес-логики
        self._build_ui()   # строим интерфейс
        self.refresh()     # загружаем данные сразу при открытии

    def _build_ui(self):
        """Создаёт все визуальные элементы вкладки."""
        root = QVBoxLayout(self)  # главный вертикальный контейнер
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        # Строка с заголовком и кнопками
        top = QHBoxLayout()
        top.addWidget(label(f"📅  {date.today().strftime('%d %B %Y')}", "title"))
        top.addStretch()  # растягивает пространство — кнопки уходят вправо
        add_btn = QPushButton("＋ Добавить")
        add_btn.clicked.connect(self._add_entry)   # clicked — сигнал, _add_entry — слот
        del_btn = QPushButton("🗑 Удалить")
        del_btn.setObjectName("danger")             # красная кнопка (из CSS #danger)
        del_btn.clicked.connect(self._delete_entry)
        top.addWidget(add_btn)
        top.addWidget(del_btn)
        root.addLayout(top)

        # Три карточки в ряд: Съедено / Цель / Осталось
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        # _stat_card возвращает (виджет_карточки, метка_значения) — сохраняем оба
        self._total_card = self._stat_card("Съедено", "0 ккал", "🔥")
        self._goal_card  = self._stat_card("Цель", "— ккал", "🎯")
        self._left_card  = self._stat_card("Осталось", "— ккал", "✅")
        cards_row.addWidget(self._total_card[0])
        cards_row.addWidget(self._goal_card[0])
        cards_row.addWidget(self._left_card[0])
        root.addLayout(cards_row)

        # Прогресс-бар: показывает % от нормы калорий
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)   # от 0% до 100%
        self._progress.setValue(0)
        self._progress.setFormat("%p%")   # формат текста внутри полосы
        self._progress.setFixedHeight(14)
        root.addWidget(self._progress)

        # Список приёмов пищи
        root.addWidget(label("Приёмы пищи", "card_title"))
        self._list = QListWidget()
        root.addWidget(self._list)

    def _stat_card(self, title: str, value: str, icon: str):
        """Создаёт одну карточку статистики. Возвращает (карточка, метка_значения)."""
        f = card()
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        lbl_title = label(f"{icon}  {title}", "card_title")
        lbl_val   = label(value, "value")  # большое число — будем обновлять через setText
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_val)
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return f, lbl_val  # возвращаем оба чтобы потом обновлять значение

    def refresh(self):
        """Перечитывает данные из хранилища и обновляет все элементы на экране."""
        stats   = self._tracker.get_day_stats()    # записи за сегодня
        profile = self._storage.load_profile()     # профиль пользователя

        self._total_card[1].setText(f"{stats.total} ккал")  # обновляем "Съедено"

        if profile:
            goal_kcal = self._tracker.get_goal_calories(profile)
            remaining = goal_kcal - stats.total
            self._goal_card[1].setText(f"{goal_kcal} ккал")
            if remaining >= 0:
                self._left_card[1].setText(f"{remaining} ккал")
                self._left_card[1].setStyleSheet(f"color: {SUCCESS}; font-size: 28px; font-weight: bold;")
            else:
                # Превышение нормы — показываем красным со знаком минус
                self._left_card[1].setText(f"−{abs(remaining)} ккал")
                self._left_card[1].setStyleSheet(f"color: {DANGER}; font-size: 28px; font-weight: bold;")
            # Процент заполнения: min(100, ...) — не даём превысить 100%
            pct = min(100, int(100 * stats.total / goal_kcal)) if goal_kcal > 0 else 0
            self._progress.setValue(pct)
            color = SUCCESS if pct <= 100 else DANGER
            self._progress.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {color}; border-radius: 6px; }}"
            )
        else:
            # Профиль не настроен — показываем заглушки
            self._goal_card[1].setText("Нет профиля")
            self._left_card[1].setText("—")
            self._progress.setValue(0)

        # Обновляем список записей
        self._list.clear()
        if not stats.entries:
            item = QListWidgetItem("  Записей нет. Нажмите «＋ Добавить»")
            item.setForeground(QColor(TEXT_MUTED))  # серый цвет для подсказки
            self._list.addItem(item)
        else:
            for e in stats.entries:
                item = QListWidgetItem(
                    f"  {e.timestamp.strftime('%H:%M')}   {e.name}   —   {e.calories} ккал"
                )
                self._list.addItem(item)

    def _add_entry(self):
        """Открывает диалог добавления блюда. Если пользователь нажал OK — сохраняет."""
        dlg = AddEntryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:  # Accepted = нажали OK
            name, cal = dlg.get_values()
            try:
                self._tracker.add_entry(name, cal)
                self.refresh()  # обновляем экран после добавления
            except TrackerError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _delete_entry(self):
        """Удаляет выбранную в списке запись после подтверждения."""
        row = self._list.currentRow()  # индекс выбранной строки (-1 если ничего не выбрано)
        stats = self._tracker.get_day_stats()
        if not stats.entries:
            QMessageBox.information(self, "Удаление", "Нет записей для удаления.")
            return
        if row < 0:
            QMessageBox.information(self, "Удаление", "Выберите запись для удаления.")
            return
        entry = stats.entries[row]
        # Спрашиваем подтверждение перед удалением
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить «{entry.name}» ({entry.calories} ккал)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._tracker.delete_entry(date.today(), row)
                self.refresh()
            except StorageError as e:
                QMessageBox.warning(self, "Ошибка", str(e))


# ── Вкладка "Статистика" ──────────────────────────────────────────────────────

class StatsTab(QWidget):
    """Вкладка со статистикой за неделю / месяц / год."""

    def __init__(self, storage: JsonStorage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)
        self._build_ui()

    def _build_ui(self):
        """Строит интерфейс: кнопки переключения периода + список результатов."""
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("📊  Статистика", "title"))

        # Кнопки выбора периода
        period_row = QHBoxLayout()
        self._period_btns: list[QPushButton] = []
        for text, period in [("Неделя", "week"), ("Месяц", "month"), ("Год", "year")]:
            btn = QPushButton(text)
            btn.setObjectName("secondary")
            # lambda с захватом p=period — иначе все кнопки будут использовать последнее значение
            btn.clicked.connect(lambda _, p=period: self._show_period(p))
            self._period_btns.append(btn)
            period_row.addWidget(btn)
        period_row.addStretch()
        root.addLayout(period_row)

        self._result_list = QListWidget()  # список строк с данными
        root.addWidget(self._result_list)

        self._total_lbl = label("", "subtitle")  # строка "Итого: X | Среднее: Y"
        root.addWidget(self._total_lbl)

        self._show_period("week")  # по умолчанию показываем неделю

    def _show_period(self, period: str):
        """Загружает и отображает статистику за выбранный период."""
        self._result_list.clear()
        try:
            if period == "week":
                stats = self._tracker.get_week_stats()
                days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                for d, cal in stats.days.items():
                    wd = days_ru[d.weekday()]  # weekday(): 0=пн, 6=вс
                    item = QListWidgetItem(f"  {wd}  {d.strftime('%d.%m')}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))  # серый для пустых дней
                    self._result_list.addItem(item)
                self._total_lbl.setText(
                    f"Итого: {stats.total} ккал  |  Среднее: {stats.daily_average:.0f} ккал/день"
                )
            elif period == "month":
                stats = self._tracker.get_month_stats()
                for d, cal in stats.days.items():
                    item = QListWidgetItem(f"  {d.strftime('%d %b')}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                self._total_lbl.setText(
                    f"Итого: {stats.total} ккал  |  Среднее: {stats.daily_average:.0f} ккал/день"
                )
            elif period == "year":
                stats = self._tracker.get_year_stats()
                months_ru = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                             "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
                for m, cal in stats.months.items():
                    item = QListWidgetItem(f"  {months_ru[m-1]}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                self._total_lbl.setText(
                    f"Итого: {stats.total} ккал  |  Среднее: {stats.monthly_average:.0f} ккал/месяц"
                )
        except StorageError as e:
            QMessageBox.warning(self, "Ошибка", str(e))


# ── Вкладка "Фото AI" ─────────────────────────────────────────────────────────

class PhotoTab(QWidget):
    """Вкладка для распознавания еды на фото через LM Studio / Ollama."""

    def __init__(self, storage: JsonStorage, today_tab: "TodayTab", parent=None):
        super().__init__(parent)
        self._storage   = storage
        self._tracker   = CalorieTracker(storage)
        self._today_tab = today_tab  # ссылка на вкладку "Сегодня" — чтобы обновить её после добавления
        self._items: list[dict] = []  # список распознанных блюд от модели
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("📷  Распознать еду по фото", "title"))
        root.addWidget(label("Используется локальная модель Ollama LLaVA", "subtitle"))
        root.addWidget(hline())

        # Строка выбора файла: поле с путём + кнопка "Выбрать"
        file_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Путь к фото...")
        self._path_edit.setReadOnly(True)  # нельзя редактировать вручную — только через диалог
        browse_btn = QPushButton("📂 Выбрать фото")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(self._path_edit)
        file_row.addWidget(browse_btn)
        root.addLayout(file_row)

        analyze_btn = QPushButton("🔍 Анализировать")
        analyze_btn.clicked.connect(self._analyze)
        root.addWidget(analyze_btn)

        self._status_lbl = label("", "subtitle")  # статус: "Анализирую...", "Найдено: 3"
        root.addWidget(self._status_lbl)

        root.addWidget(label("Распознанные блюда:", "card_title"))
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)  # можно выбрать несколько
        root.addWidget(self._list)

        add_btn = QPushButton("✓ Добавить выбранные")
        add_btn.clicked.connect(self._add_selected)
        root.addWidget(add_btn)

    def _browse(self):
        """Открывает системный диалог выбора файла изображения."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите фото", "",
            "Изображения (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if path:
            self._path_edit.setText(path)

    def _analyze(self):
        """Отправляет фото в модель и показывает распознанные блюда."""
        path = self._path_edit.text()
        if not path:
            QMessageBox.warning(self, "Ошибка", "Выберите фото.")
            return
        self._status_lbl.setText("⏳ Анализирую...")
        self._list.clear()
        self._items = []
        QApplication.processEvents()  # обновляем UI прямо сейчас (иначе "Анализирую" не появится)
        try:
            from calorie_tracker.vision import recognize_food
            items = recognize_food(path)  # отправляем в LM Studio / Ollama
            self._items = items
            if not items:
                self._status_lbl.setText("Еда не распознана.")
            else:
                self._status_lbl.setText(f"Найдено блюд: {len(items)}. Выберите нужные и нажмите «Добавить».")
                for item in items:
                    self._list.addItem(f"  {item['name']}  —  {item['calories']} ккал")
                self._list.selectAll()  # выбираем все по умолчанию
        except TrackerError as e:
            self._status_lbl.setText(f"Ошибка: {e}")

    def _add_selected(self):
        """Добавляет выбранные пользователем блюда в трекер."""
        # selectedItems() возвращает список выбранных элементов
        selected = [self._list.row(i) for i in self._list.selectedItems()]
        if not selected:
            QMessageBox.information(self, "Добавление", "Ничего не выбрано.")
            return
        added = 0
        for idx in selected:
            item = self._items[idx]
            try:
                self._tracker.add_entry(item["name"], item["calories"])
                added += 1
            except TrackerError as e:
                QMessageBox.warning(self, "Ошибка", str(e))
        if added:
            self._today_tab.refresh()  # обновляем вкладку "Сегодня"
            QMessageBox.information(self, "Готово", f"Добавлено блюд: {added}")


# ── Вкладка "Профиль" ─────────────────────────────────────────────────────────

class ProfileTab(QWidget):
    """Вкладка с информацией о профиле и кнопкой редактирования."""

    def __init__(self, storage: JsonStorage, today_tab: "TodayTab", parent=None):
        super().__init__(parent)
        self._storage   = storage
        self._tracker   = CalorieTracker(storage)
        self._today_tab = today_tab  # после изменения профиля обновляем "Сегодня"
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("👤  Профиль и цель", "title"))
        root.addWidget(hline())

        # Карточка с данными профиля — будем динамически заполнять в refresh()
        self._info_card   = card()
        self._info_layout = QVBoxLayout(self._info_card)
        self._info_layout.setContentsMargins(16, 12, 16, 12)
        root.addWidget(self._info_card)

        edit_btn = QPushButton("✏️  Редактировать профиль")
        edit_btn.clicked.connect(self._edit_profile)
        root.addWidget(edit_btn)
        root.addStretch()  # прижимаем кнопку к верху

    def refresh(self):
        """Очищает карточку и заново заполняет данными из профиля."""
        # Удаляем все старые виджеты из карточки
        while self._info_layout.count():
            child = self._info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()  # deleteLater — безопасное удаление в Qt

        profile = self._storage.load_profile()
        if not profile:
            # Профиль не создан — показываем подсказку
            self._info_layout.addWidget(label("Профиль не настроен.", "subtitle"))
            self._info_layout.addWidget(label("Нажмите «Редактировать профиль» для настройки.", "subtitle"))
            return

        goal_kcal  = self._tracker.get_goal_calories(profile)
        goal_names = {GoalMode.LOSS: "🔥 Похудение", GoalMode.MAINTAIN: "⚖️ Поддержание", GoalMode.GAIN: "💪 Набор массы"}
        act_names  = {
            ActivityLevel.SEDENTARY:   "Сидячий",
            ActivityLevel.LIGHT:       "Лёгкая",
            ActivityLevel.MODERATE:    "Умеренная",
            ActivityLevel.ACTIVE:      "Высокая",
            ActivityLevel.VERY_ACTIVE: "Очень высокая",
        }
        sex = "Мужской" if profile.male else "Женский"

        # Список строк: (название, значение)
        rows = [
            ("Вес",           f"{profile.weight_kg} кг"),
            ("Рост",          f"{profile.height_cm} см"),
            ("Возраст",       f"{profile.age} лет"),
            ("Пол",           sex),
            ("Активность",    act_names[profile.activity]),
            ("Цель",          goal_names[profile.goal]),
            ("Норма калорий", f"{goal_kcal} ккал/день"),
        ]
        for title, val in rows:
            row_w = QHBoxLayout()
            row_w.addWidget(label(title, "card_title"))
            row_w.addStretch()
            row_w.addWidget(label(val))
            self._info_layout.addLayout(row_w)
            self._info_layout.addWidget(hline())

    def _edit_profile(self):
        """Открывает диалог редактирования профиля и сохраняет изменения."""
        profile = self._storage.load_profile()
        dlg = ProfileDialog(profile, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_profile = dlg.get_profile()
            try:
                self._storage.save_profile(new_profile)
                self.refresh()              # обновляем эту вкладку
                self._today_tab.refresh()   # обновляем "Сегодня" (норма калорий могла измениться)
            except StorageError as e:
                QMessageBox.warning(self, "Ошибка", str(e))


# ── Главное окно ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Главное окно приложения — содержит шапку и вкладки."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🥗 Calorie Tracker")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(STYLE)

        self._storage = JsonStorage()  # одно хранилище на всё приложение

        central = QWidget()
        self.setCentralWidget(central)  # центральный виджет — обязателен для QMainWindow
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Шапка приложения
        header = QWidget()
        header.setStyleSheet(f"background-color: {PANEL_BG}; border-bottom: 1px solid {BORDER};")
        header.setFixedHeight(56)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        title_lbl = label("🥗  Calorie Tracker", "title")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY};")
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()
        root.addWidget(header)

        # Создаём все четыре вкладки
        tabs = QTabWidget()
        tabs.setDocumentMode(True)  # убирает рамку вокруг вкладок

        self._today_tab   = TodayTab(self._storage)
        self._stats_tab   = StatsTab(self._storage)
        self._photo_tab   = PhotoTab(self._storage, self._today_tab)
        self._profile_tab = ProfileTab(self._storage, self._today_tab)

        tabs.addTab(self._today_tab,   "📅  Сегодня")
        tabs.addTab(self._stats_tab,   "📊  Статистика")
        tabs.addTab(self._photo_tab,   "📷  Фото AI")
        tabs.addTab(self._profile_tab, "👤  Профиль")

        # currentChanged — сигнал который срабатывает при переключении вкладки
        tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(tabs)

    def _on_tab_changed(self, idx: int):
        """Обновляет данные при переключении на вкладку."""
        if idx == 0:
            self._today_tab.refresh()    # "Сегодня" — перечитываем записи
        elif idx == 1:
            self._stats_tab._show_period("week")  # "Статистика" — показываем неделю
        elif idx == 3:
            self._profile_tab.refresh()  # "Профиль" — перечитываем профиль


# ── Точка входа ───────────────────────────────────────────────────────────────

def run_app() -> int:
    """Создаёт приложение, показывает окно и запускает главный цикл событий."""
    app = QApplication(sys.argv)  # QApplication должен быть создан до любых виджетов
    app.setStyle("Fusion")        # стиль Fusion — одинаково выглядит на всех ОС
    window = MainWindow()
    window.show()                 # показываем окно
    return app.exec()             # запускаем цикл событий (блокирует до закрытия окна)
