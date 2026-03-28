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
QLabel {{
    background-color: transparent;
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
    border: 1px solid {ACCENT};
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
    border: 1px solid {ACCENT};
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
    background-color: transparent;
}}
QLabel#subtitle {{
    font-size: 14px;
    color: {TEXT_MUTED};
    background-color: transparent;
}}
QLabel#card_title {{
    font-size: 13px;
    font-weight: bold;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    background-color: transparent;
}}
QLabel#value {{
    font-size: 28px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
    background-color: transparent;
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
    background-color: #3a3a55;
    border-radius: 12px;
    border: 1px solid {ACCENT};
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


# ── Диалог просмотра записей за день ─────────────────────────────────────────

class DayDetailDialog(QDialog):
    """Всплывающее окно с подробной статистикой за выбранный день."""

    def __init__(self, day: date, tracker: CalorieTracker, storage: JsonStorage, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📅  {day.strftime('%d %B %Y')}")
        self.setMinimumWidth(420)
        self.setMinimumHeight(320)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        layout.addWidget(label(f"📅  {day.strftime('%d %B %Y')}", "title"))
        layout.addWidget(hline())

        # Загружаем данные
        stats = tracker.get_day_stats(day)
        profile = storage.load_profile()

        # Карточки: съедено / цель / осталось
        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)

        def mini_card(title: str, value: str, color: str = TEXT_PRIMARY) -> QFrame:
            f = card()
            lay = QVBoxLayout(f)
            lay.setContentsMargins(12, 8, 12, 8)
            lay.setSpacing(2)
            lay.addWidget(label(title, "card_title"))
            val_lbl = label(value, "value")
            val_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
            lay.addWidget(val_lbl)
            return f

        cards_row.addWidget(mini_card("🔥 Съедено", f"{stats.total} ккал"))

        if profile:
            goal_kcal = tracker.get_goal_calories(profile)
            remaining = goal_kcal - stats.total
            cards_row.addWidget(mini_card("🎯 Цель", f"{goal_kcal} ккал"))
            color = SUCCESS if remaining >= 0 else DANGER
            rem_text = f"{remaining} ккал" if remaining >= 0 else f"−{abs(remaining)} ккал"
            cards_row.addWidget(mini_card("✅ Осталось", rem_text, color))
        else:
            cards_row.addWidget(mini_card("🎯 Цель", "нет профиля"))

        layout.addLayout(cards_row)
        layout.addWidget(hline())

        # Список записей
        layout.addWidget(label("Приёмы пищи:", "card_title"))
        lst = QListWidget()
        if not stats.entries:
            item = QListWidgetItem("  Записей нет")
            item.setForeground(QColor(TEXT_MUTED))
            lst.addItem(item)
        else:
            for e in stats.entries:
                lst.addItem(f"  {e.timestamp.strftime('%H:%M')}   {e.name}   —   {e.calories} ккал")
        layout.addWidget(lst)

        # Кнопка закрыть
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ── Вкладка "Статистика" ──────────────────────────────────────────────────────

class StatsTab(QWidget):
    """Вкладка со статистикой за неделю / месяц / год. Клик на день — детали."""

    def __init__(self, storage: JsonStorage, parent=None):
        super().__init__(parent)
        self._storage = storage
        self._tracker = CalorieTracker(storage)
        self._dates: list[date] = []  # список дат соответствующих строкам списка
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
            btn.clicked.connect(lambda _, p=period: self._show_period(p))
            self._period_btns.append(btn)
            period_row.addWidget(btn)
        period_row.addStretch()
        root.addLayout(period_row)

        hint = label("💡 Нажмите на день чтобы увидеть подробности", "subtitle")
        root.addWidget(hint)

        self._result_list = QListWidget()
        # Двойной клик или одиночный — открываем детали дня
        self._result_list.itemDoubleClicked.connect(self._on_day_clicked)
        self._result_list.itemClicked.connect(self._on_day_clicked)
        root.addWidget(self._result_list)

        # Итоговая карточка — две колонки: Итого и Среднее
        self._summary_card = card()
        self._summary_card.setStyleSheet(
            f"background-color: {ACCENT}; border-radius: 12px; border: none;"
        )
        summary_lay = QHBoxLayout(self._summary_card)
        summary_lay.setContentsMargins(20, 12, 20, 12)
        summary_lay.setSpacing(0)

        self._total_lbl = QLabel("—")
        self._total_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        self._avg_lbl = QLabel("—")
        self._avg_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: #ffffff;"
        )
        self._avg_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        summary_lay.addWidget(self._total_lbl)
        summary_lay.addStretch()
        summary_lay.addWidget(self._avg_lbl)
        root.addWidget(self._summary_card)

        self._show_period("week")

    def _on_day_clicked(self, item: QListWidgetItem):
        """Открывает диалог с деталями дня при клике на строку."""
        row = self._result_list.row(item)
        if row < 0 or row >= len(self._dates):
            return
        day = self._dates[row]
        # Для года кликаем на месяц — показываем статистику месяца
        if not isinstance(day, date):
            return
        dlg = DayDetailDialog(day, self._tracker, self._storage, self)
        dlg.exec()

    def _show_period(self, period: str):
        """Загружает и отображает статистику за выбранный период."""
        self._result_list.clear()
        self._dates = []
        try:
            if period == "week":
                stats = self._tracker.get_week_stats()
                days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                for d, cal in stats.days.items():
                    wd = days_ru[d.weekday()]
                    item = QListWidgetItem(f"  {wd}  {d.strftime('%d.%m')}   —   {cal} ккал  🔍")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                    self._dates.append(d)
                self._total_lbl.setText(f"🔥 Итого: {stats.total} ккал")
                self._avg_lbl.setText(f"Среднее: {stats.daily_average:.0f} ккал/день")
            elif period == "month":
                stats = self._tracker.get_month_stats()
                for d, cal in stats.days.items():
                    item = QListWidgetItem(f"  {d.strftime('%d %b')}   —   {cal} ккал  🔍")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                    self._dates.append(d)
                self._total_lbl.setText(f"🔥 Итого: {stats.total} ккал")
                self._avg_lbl.setText(f"Среднее: {stats.daily_average:.0f} ккал/день")
            elif period == "year":
                stats = self._tracker.get_year_stats()
                months_ru = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                             "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
                today = date.today()
                for m, cal in stats.months.items():
                    item = QListWidgetItem(f"  {months_ru[m-1]}   —   {cal} ккал")
                    if cal == 0:
                        item.setForeground(QColor(TEXT_MUTED))
                    self._result_list.addItem(item)
                    self._dates.append(date(today.year, m, 1))
                self._total_lbl.setText(f"🔥 Итого: {stats.total} ккал")
                self._avg_lbl.setText(f"Среднее: {stats.monthly_average:.0f} ккал/месяц")
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

        # Список строк: (название, значение, цвет_названия, цвет_значения)
        rows = [
            ("Вес",           f"{profile.weight_kg} кг",    "#7dd3fc", "#7dd3fc"),
            ("Рост",          f"{profile.height_cm} см",    "#86efac", "#86efac"),
            ("Возраст",       f"{profile.age} лет",         "#fcd34d", "#fcd34d"),
            ("Пол",           sex,                          "#f9a8d4", "#f9a8d4"),
            ("Активность",    act_names[profile.activity],  "#c4b5fd", "#c4b5fd"),
            ("Цель",          goal_names[profile.goal],     WARNING,   WARNING),
            ("Норма калорий", f"{goal_kcal} ккал/день",     SUCCESS,   SUCCESS),
        ]
        for title, val, title_color, val_color in rows:
            row_w = QHBoxLayout()
            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet(
                f"font-size: 11px; font-weight: bold; color: {title_color}; letter-spacing: 1px;"
            )
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {val_color};"
            )
            row_w.addWidget(title_lbl)
            row_w.addStretch()
            row_w.addWidget(val_lbl)
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


# ── Вкладка "База продуктов" ──────────────────────────────────────────────────

class FoodDBTab(QWidget):
    """Вкладка: выбор продукта из базы + ввод граммов → автоматический расчёт калорий."""

    def __init__(self, storage: JsonStorage, today_tab: "TodayTab", parent=None):
        super().__init__(parent)
        self._storage   = storage
        self._tracker   = CalorieTracker(storage)
        self._today_tab = today_tab
        self._db        = self._load_db()
        self._filtered  = self._db
        self._selected: dict | None = None
        self._build_ui()

    def _load_db(self) -> list[dict]:
        import json
        from pathlib import Path
        db_path = Path(__file__).parent / "food_db.json"
        if not db_path.exists():
            return []
        return json.loads(db_path.read_text(encoding="utf-8"))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(label("🥦  База продуктов", "title"))
        root.addWidget(label("Выберите продукт, укажите граммы — калории посчитаются автоматически", "subtitle"))
        root.addWidget(hline())

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск продукта...")
        self._search.textChanged.connect(self._filter_list)
        root.addWidget(self._search)

        self._list = QListWidget()
        self._list.setMaximumHeight(220)
        self._list.itemClicked.connect(self._on_select)
        self._fill_list(self._db)
        root.addWidget(self._list)

        root.addWidget(hline())

        form = QFormLayout()
        form.setSpacing(10)

        self._selected_lbl = QLabel("—")
        self._selected_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {ACCENT};")
        form.addRow("Продукт:", self._selected_lbl)

        self._kcal_lbl = QLabel("— ккал/100г")
        self._kcal_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT_MUTED};")
        form.addRow("Калорийность:", self._kcal_lbl)

        self._grams = QSpinBox()
        self._grams.setRange(1, 9999)
        self._grams.setValue(100)
        self._grams.setSuffix(" г")
        self._grams.valueChanged.connect(self._update_result)
        form.addRow("Количество:", self._grams)

        root.addLayout(form)

        result_card = card()
        result_lay = QHBoxLayout(result_card)
        result_lay.setContentsMargins(20, 12, 20, 12)
        self._result_lbl = QLabel("0 ккал")
        self._result_lbl.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {SUCCESS};")
        result_lay.addWidget(label("Итого:", "card_title"))
        result_lay.addStretch()
        result_lay.addWidget(self._result_lbl)
        root.addWidget(result_card)

        add_btn = QPushButton("＋ Добавить в дневник")
        add_btn.clicked.connect(self._add_to_diary)
        root.addWidget(add_btn)

        custom_btn = QPushButton("+ Добавить свой продукт в базу")
        custom_btn.setObjectName("secondary")
        custom_btn.clicked.connect(self._add_custom_product)
        root.addWidget(custom_btn)

    def _fill_list(self, items: list[dict]):
        self._list.clear()
        for item in items:
            self._list.addItem(f"  {item['name']}  —  {item['kcal_per_100g']} ккал/100г")

    def _filter_list(self, text: str):
        self._filtered = [p for p in self._db if text.lower() in p["name"].lower()]
        self._fill_list(self._filtered)

    def _on_select(self, item: QListWidgetItem):
        row = self._list.row(item)
        if row < 0 or row >= len(self._filtered):
            return
        self._selected = self._filtered[row]
        self._selected_lbl.setText(self._selected["name"])
        self._kcal_lbl.setText(f"{self._selected['kcal_per_100g']} ккал/100г")
        self._update_result()

    def _update_result(self):
        if not self._selected:
            return
        kcal = round(self._selected["kcal_per_100g"] * self._grams.value() / 100)
        self._result_lbl.setText(f"{kcal} ккал")

    def _add_to_diary(self):
        if not self._selected:
            QMessageBox.information(self, "Выбор", "Сначала выберите продукт из списка.")
            return
        grams = self._grams.value()
        kcal  = round(self._selected["kcal_per_100g"] * grams / 100)
        name  = f"{self._selected['name']} ({grams}г)"
        try:
            self._tracker.add_entry(name, kcal)
            self._today_tab.refresh()
            QMessageBox.information(self, "Добавлено", f"{name} — {kcal} ккал")
        except TrackerError as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def _add_custom_product(self):
        import json
        from pathlib import Path
        dlg = QDialog(self)
        dlg.setWindowTitle("Добавить продукт")
        dlg.setMinimumWidth(340)
        dlg.setStyleSheet(STYLE)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)
        lay.addWidget(label("Новый продукт", "title"))
        form = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название продукта")
        kcal_spin = QSpinBox()
        kcal_spin.setRange(0, 9999)
        kcal_spin.setSuffix(" ккал/100г")
        form.addRow("Название:", name_edit)
        form.addRow("Калорийность:", kcal_spin)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Введите название продукта.")
                return
            new_item = {"name": name, "kcal_per_100g": kcal_spin.value()}
            self._db.append(new_item)
            self._filtered = self._db
            db_path = Path(__file__).parent / "food_db.json"
            db_path.write_text(
                json.dumps(self._db, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._fill_list(self._db)
            QMessageBox.information(self, "Готово", f"Продукт «{name}» добавлен в базу.")


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

        # Создаём все пять вкладок
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        self._today_tab   = TodayTab(self._storage)
        self._stats_tab   = StatsTab(self._storage)
        self._food_tab    = FoodDBTab(self._storage, self._today_tab)
        self._photo_tab   = PhotoTab(self._storage, self._today_tab)
        self._profile_tab = ProfileTab(self._storage, self._today_tab)

        tabs.addTab(self._today_tab,   "📅  Сегодня")
        tabs.addTab(self._stats_tab,   "📊  Статистика")
        tabs.addTab(self._food_tab,    "🥦  Продукты")
        tabs.addTab(self._photo_tab,   "📷  Фото AI")
        tabs.addTab(self._profile_tab, "👤  Профиль")

        tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(tabs)

    def _on_tab_changed(self, idx: int):
        if idx == 0:
            self._today_tab.refresh()
        elif idx == 1:
            self._stats_tab._show_period("week")
        elif idx == 4:
            self._profile_tab.refresh()


# ── Точка входа ───────────────────────────────────────────────────────────────

def run_app() -> int:
    """Создаёт приложение, показывает окно и запускает главный цикл событий."""
    app = QApplication(sys.argv)  # QApplication должен быть создан до любых виджетов
    app.setStyle("Fusion")        # стиль Fusion — одинаково выглядит на всех ОС
    # Segoe UI Emoji — шрифт Windows с поддержкой эмодзи, убирает чёрные квадраты
    font = QFont("Segoe UI Emoji", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()                 # показываем окно
    return app.exec()             # запускаем цикл событий (блокирует до закрытия окна)
