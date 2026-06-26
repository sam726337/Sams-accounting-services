from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sams_accounting_desktop.ui.components import AppButton, StatusChip
from sams_accounting_desktop.ui.icons import make_icon


class SalesChoicePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("workspace")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(self.header())

        choice_row = QHBoxLayout()
        choice_row.setSpacing(18)
        choice_row.addWidget(
            self.choice_card(
                "Random Sale",
                "Auto-generated invoice flow",
                "Fast preview",
                "#be123c",
                "RS",
                self.select_random_sale,
            )
        )
        choice_row.addWidget(
            self.choice_card(
                "Fixed Sale",
                "Manual invoice flow",
                "Controlled entry",
                "#0f766e",
                "FS",
                self.select_fixed_sale,
            )
        )
        layout.addLayout(choice_row)

        self.selection_status = StatusChip("Select sales mode", "info")
        layout.addWidget(self.selection_status)
        layout.addStretch()

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Sales Generator")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Choose sales creation mode")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack)
        layout.addStretch()
        layout.addWidget(StatusChip("Ready", "info"))
        return header

    def choice_card(
        self,
        title: str,
        subtitle: str,
        badge: str,
        accent: str,
        initials: str,
        handler,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("choiceCard")
        card.setMinimumHeight(260)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(make_icon(initials, accent, 54, 12).pixmap(54, 54))
        top.addWidget(icon)
        top.addStretch()
        chip = QLabel(badge)
        chip.setObjectName("badge")
        top.addWidget(chip)
        layout.addLayout(top)

        heading = QLabel(title)
        heading.setObjectName("choiceTitle")
        layout.addWidget(heading)

        body = QLabel(subtitle)
        body.setObjectName("choiceBody")
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        button = AppButton(f"Open {title}", "primary", initials, accent)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return card

    def select_random_sale(self):
        self.selection_status.set_status("warning", "Random Sale selected")

    def select_fixed_sale(self):
        self.selection_status.set_status("ok", "Fixed Sale selected")
