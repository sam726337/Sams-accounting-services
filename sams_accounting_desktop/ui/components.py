from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from sams_accounting_desktop.data import ACTIVITY
from sams_accounting_desktop.models import Module
from sams_accounting_desktop.ui.icons import make_icon


class AppButton(QPushButton):
    def __init__(self, text: str, variant: str = "secondary", icon_text: str = "", icon_color: str = "#0f766e"):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName(f"{variant}Button")
        self.setMinimumHeight(38)
        if icon_text:
            self.setIcon(make_icon(icon_text, icon_color, 24, 6))
            self.setIconSize(QSize(24, 24))


class NavItem(QPushButton):
    def __init__(self, label: str, initials: str, active: bool = False):
        super().__init__(label)
        self.label = label
        self.initials = initials
        self.compact = False
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setToolTip(label)
        self.setIconSize(QSize(30, 30))
        self.setMinimumHeight(46)
        self.set_active(active)

    def set_active(self, active: bool):
        self.setChecked(active)
        self.setText("" if self.compact else self.label)
        self.setIcon(make_icon(self.initials, "#14b8a6" if active else "#344054", 30, 7))
        self.setObjectName("navActive" if active else "navItem")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_compact(self, compact: bool):
        self.compact = compact
        self.setText("" if compact else self.label)
        self.setToolTip(self.label)
        self.setMinimumWidth(46 if compact else 0)


class KpiCard(QFrame):
    def __init__(self, label: str, value: str, helper: str, accent: str):
        super().__init__()
        self.setObjectName("kpiCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        head = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(9, 9)
        dot.setStyleSheet(f"background: {accent}; border-radius: 4px;")
        title = QLabel(label)
        title.setObjectName("mutedLabel")
        head.addWidget(dot)
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        number = QLabel(value)
        number.setObjectName("kpiValue")
        layout.addWidget(number)

        hint = QLabel(helper)
        hint.setObjectName("smallText")
        hint.setWordWrap(True)
        layout.addWidget(hint)


class StatusChip(QLabel):
    STATUS_NAMES = {
        "ok": "statusOk",
        "warning": "statusWarning",
        "error": "statusError",
        "idle": "statusIdle",
        "info": "statusInfo",
    }

    def __init__(self, text: str, status: str = "idle"):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(status, text)

    def set_status(self, status: str, text: str | None = None):
        if text is not None:
            self.setText(text)
        self.setObjectName(self.STATUS_NAMES.get(status, "statusIdle"))
        self.style().unpolish(self)
        self.style().polish(self)


class InsightCard(QFrame):
    def __init__(self, title: str, value: str, detail: str, accent: str, initials: str):
        super().__init__()
        self.setObjectName("insightCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setPixmap(make_icon(initials, accent, 36, 8).pixmap(36, 36))
        layout.addWidget(icon)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        label = QLabel(title)
        label.setObjectName("mutedLabel")
        number = QLabel(value)
        number.setObjectName("insightValue")
        helper = QLabel(detail)
        helper.setObjectName("smallText")
        helper.setWordWrap(True)
        copy.addWidget(label)
        copy.addWidget(number)
        copy.addWidget(helper)
        layout.addLayout(copy, 1)


class WorkflowStepper(QFrame):
    def __init__(self, steps: list[str]):
        super().__init__()
        self.setObjectName("stepperPanel")
        self.steps = steps
        self.step_frames: list[QFrame] = []
        self.step_labels: list[QLabel] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        for index, step in enumerate(steps):
            frame = QFrame()
            frame.setObjectName("stepIdle")
            frame_layout = QHBoxLayout(frame)
            frame_layout.setContentsMargins(10, 8, 10, 8)
            frame_layout.setSpacing(8)

            number = QLabel(str(index + 1))
            number.setObjectName("stepNumber")
            number.setAlignment(Qt.AlignCenter)
            title = QLabel(step)
            title.setObjectName("stepLabel")
            title.setWordWrap(True)
            frame_layout.addWidget(number)
            frame_layout.addWidget(title, 1)
            layout.addWidget(frame, 1)

            self.step_frames.append(frame)
            self.step_labels.append(title)

        self.set_active(0)

    def set_active(self, active_index: int):
        for index, frame in enumerate(self.step_frames):
            if index < active_index:
                name = "stepDone"
            elif index == active_index:
                name = "stepActive"
            else:
                name = "stepIdle"
            frame.setObjectName(name)
            frame.style().unpolish(frame)
            frame.style().polish(frame)


class ModuleCard(QFrame):
    open_requested = Signal(str)

    def __init__(self, module: Module):
        super().__init__()
        self.module = module
        self.setObjectName("moduleCard")
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(4)
        accent.setStyleSheet(f"background: {module.accent}; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        layout.addWidget(accent)

        body = QVBoxLayout()
        body.setContentsMargins(20, 18, 20, 18)
        body.setSpacing(14)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(make_icon(module.initials, module.accent, 42, 9).pixmap(42, 42))
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel(module.title)
        title.setObjectName("cardTitle")
        title_stack.addWidget(title)
        header.addWidget(icon)
        header.addLayout(title_stack)
        header.addStretch()

        badge = QLabel(module.metric)
        badge.setObjectName("badge")
        header.addWidget(badge)
        body.addLayout(header)

        subtitle = QLabel(module.subtitle)
        subtitle.setObjectName("cardBody")
        subtitle.setWordWrap(True)
        body.addWidget(subtitle)
        body.addStretch()

        open_button = AppButton("Open", "primary")
        open_button.clicked.connect(lambda: self.open_requested.emit(self.module.title))
        body.addWidget(open_button)

        layout.addLayout(body)


class ActivityTable(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("activityPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Recent Activity")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(AppButton("View all", "secondary"))
        layout.addLayout(header)

        table = QTableWidget(len(ACTIVITY), 4)
        table.setObjectName("activityTable")
        table.setHorizontalHeaderLabels(["Time", "Module", "Description", "Status"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        for row, activity in enumerate(ACTIVITY):
            for column, value in enumerate([activity.time, activity.module, activity.description, activity.status]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 3:
                    item.setForeground(QColor("#0f766e"))
                table.setItem(row, column, item)

        table.setFixedHeight(178)
        layout.addWidget(table)
