from PySide6.QtCore import Qt, QSize
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
    def __init__(self, text: str, variant: str = "secondary"):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName(f"{variant}Button")
        self.setMinimumHeight(38)


class NavItem(QPushButton):
    def __init__(self, label: str, initials: str, active: bool = False):
        super().__init__(label)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setChecked(active)
        self.setIcon(make_icon(initials, "#14b8a6" if active else "#344054", 30, 7))
        self.setIconSize(QSize(30, 30))
        self.setMinimumHeight(46)
        self.setObjectName("navActive" if active else "navItem")


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


class ModuleCard(QFrame):
    def __init__(self, module: Module):
        super().__init__()
        self.setObjectName("moduleCard")
        self.setMinimumHeight(205)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(4)
        accent.setStyleSheet(f"background: {module.accent}; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        layout.addWidget(accent)

        body = QVBoxLayout()
        body.setContentsMargins(18, 16, 18, 16)
        body.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(make_icon(module.initials, module.accent, 42, 9).pixmap(42, 42))
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel(module.title)
        title.setObjectName("cardTitle")
        state = QLabel(module.state)
        state.setObjectName("stateText")
        title_stack.addWidget(title)
        title_stack.addWidget(state)
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

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(AppButton("Open", "primary"))
        actions.addWidget(AppButton("History", "secondary"))
        actions.addStretch()
        body.addLayout(actions)

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
