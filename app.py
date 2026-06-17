import sys
from dataclasses import dataclass

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "Sam's Accounting Desktop"
APP_VERSION = "v1.0.1"


@dataclass(frozen=True)
class ModuleCard:
    title: str
    description: str
    status: str
    accent: str


MODULES = [
    ModuleCard(
        "Tally",
        "Localhost Tally Prime connection, company aur masters fetch karein.",
        "Connection",
        "#0f766e",
    ),
    ModuleCard(
        "Excel",
        "Excel bank rows review karein, ledgers fill karein, phir Tally me import karein.",
        "Review",
        "#2563eb",
    ),
    ModuleCard(
        "Bank PDF",
        "Statement parse karke Payment/Receipt vouchers direct Tally me bhejein.",
        "Parser",
        "#7c3aed",
    ),
    ModuleCard(
        "Image PDF",
        "Scanned statement parse karke ledger mapping ke saath Tally posting karein.",
        "OCR",
        "#c2410c",
    ),
    ModuleCard(
        "Purchase Reco",
        "GST portal purchase Excel ko Tally purchase vouchers ke saath reconcile karein.",
        "GST",
        "#15803d",
    ),
    ModuleCard(
        "Sales",
        "Random sales invoice preview generate karke direct Tally me create karein.",
        "Invoice",
        "#be123c",
    ),
    ModuleCard(
        "Voucher Entry",
        "Journal, Payment, Receipt, Purchase/Sales ya custom 2-ledger voucher add karein.",
        "Manual",
        "#334155",
    ),
]


def initials_icon(text: str, color: str, size: int = 42) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 8, 8)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)


class NavButton(QPushButton):
    def __init__(self, text: str, active: bool = False):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(initials_icon(text[:2].upper(), "#14b8a6" if active else "#334155", 30))
        self.setIconSize(QSize(30, 30))
        self.setMinimumHeight(46)
        self.setCheckable(True)
        self.setChecked(active)
        self.setObjectName("navActive" if active else "navButton")


class MetricPill(QFrame):
    def __init__(self, label: str, value: str):
        super().__init__()
        self.setObjectName("metricPill")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        label_widget = QLabel(label)
        label_widget.setObjectName("metricLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("metricValue")

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)


class AccountingModuleCard(QFrame):
    def __init__(self, module: ModuleCard):
        super().__init__()
        self.setObjectName("moduleCard")
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(4)
        accent.setStyleSheet(f"background: {module.accent}; border-radius: 0;")
        layout.addWidget(accent)

        body = QVBoxLayout()
        body.setContentsMargins(18, 16, 18, 18)
        body.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(module.title)
        title.setObjectName("cardTitle")
        status = QLabel(module.status)
        status.setObjectName("statusBadge")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(status)
        body.addLayout(header)

        description = QLabel(module.description)
        description.setObjectName("cardDescription")
        description.setWordWrap(True)
        body.addWidget(description)
        body.addStretch()

        actions = QHBoxLayout()
        open_button = QPushButton("Open")
        open_button.setObjectName("primaryButton")
        history_button = QPushButton("History")
        history_button.setObjectName("ghostButton")
        actions.addWidget(open_button)
        actions.addWidget(history_button)
        actions.addStretch()
        body.addLayout(actions)

        layout.addLayout(body)


class SamsAccountingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1080, 700)
        self.resize(1200, 760)
        self.setWindowIcon(initials_icon("SA", "#0f766e", 64))

        shell = QWidget()
        shell.setObjectName("shell")
        root = QHBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self.build_sidebar())
        root.addWidget(self.build_workspace(), 1)

        self.setCentralWidget(shell)
        self.apply_styles()

    def build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(268)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 18)
        layout.setSpacing(8)

        brand = QHBoxLayout()
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(initials_icon("SA", "#14b8a6", 44).pixmap(44, 44))
        brand_text = QVBoxLayout()
        name = QLabel("Sam's Accounting")
        name.setObjectName("brandName")
        subtitle = QLabel("Desktop workspace")
        subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(name)
        brand_text.addWidget(subtitle)
        brand.addWidget(logo)
        brand.addLayout(brand_text)
        layout.addLayout(brand)
        layout.addSpacing(18)

        for index, item in enumerate(
            ["Dashboard", "Tally", "Excel", "Bank PDF", "Image PDF", "Purchase Reco", "Sales", "Voucher Entry"]
        ):
            layout.addWidget(NavButton(item, active=index == 0))

        layout.addStretch()

        account = QFrame()
        account.setObjectName("accountPanel")
        account_layout = QVBoxLayout(account)
        account_layout.setContentsMargins(14, 13, 14, 13)
        account_layout.setSpacing(3)
        account_label = QLabel("Subscription")
        account_label.setObjectName("accountLabel")
        account_value = QLabel("Verified")
        account_value.setObjectName("accountValue")
        account_layout.addWidget(account_label)
        account_layout.addWidget(account_value)
        layout.addWidget(account)

        return sidebar

    def build_workspace(self) -> QWidget:
        workspace = QWidget()
        workspace.setObjectName("workspace")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(22)

        layout.addWidget(self.build_topbar())
        layout.addWidget(self.build_hero())
        layout.addLayout(self.build_cards_grid(), 1)

        return workspace

    def build_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setMinimumHeight(74)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(16)

        title_stack = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        meta = QLabel("Logged in: sameer mansuri | Subscription: Verified | AI credit: Rs 500.0000")
        meta.setObjectName("pageMeta")
        title_stack.addWidget(title)
        title_stack.addWidget(meta)
        layout.addLayout(title_stack)
        layout.addStretch()

        check_tally = QPushButton("Check Tally")
        check_tally.setObjectName("ghostButton")
        new_voucher = QPushButton("New Voucher")
        new_voucher.setObjectName("primaryButton")
        layout.addWidget(check_tally)
        layout.addWidget(new_voucher)

        return topbar

    def build_hero(self) -> QWidget:
        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero.setMinimumHeight(128)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(24, 20, 20, 20)
        layout.setSpacing(16)

        copy = QVBoxLayout()
        eyebrow = QLabel("Control center")
        eyebrow.setObjectName("eyebrow")
        headline = QLabel("Accounting automation dashboard")
        headline.setObjectName("heroTitle")
        body = QLabel("Desktop se direct Tally Prime posting, CSV backup optional.")
        body.setObjectName("heroBody")
        copy.addWidget(eyebrow)
        copy.addWidget(headline)
        copy.addWidget(body)
        layout.addLayout(copy, 1)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        metrics.addWidget(MetricPill("Tally", "Ready"))
        metrics.addWidget(MetricPill("AI Credit", "Rs 500"))
        metrics.addWidget(MetricPill("Version", APP_VERSION))
        layout.addLayout(metrics)

        return hero

    def build_cards_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        for index, module in enumerate(MODULES):
            grid.addWidget(AccountingModuleCard(module), index // 3, index % 3)

        grid.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), 3, 2)
        return grid

    def apply_styles(self):
        self.setStyleSheet(
            """
            QWidget#shell {
                background: #eef2f6;
                font-family: Segoe UI;
                color: #101828;
            }

            QFrame#sidebar {
                background: #101828;
            }

            QLabel#brandName {
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
            }

            QLabel#brandSubtitle {
                color: #98a2b3;
                font-size: 11px;
            }

            QPushButton#navButton,
            QPushButton#navActive {
                border: 0;
                border-radius: 7px;
                text-align: left;
                padding: 8px 12px;
                color: #d0d5dd;
                background: transparent;
                font-size: 13px;
            }

            QPushButton#navButton:hover {
                background: #1d2939;
                color: #ffffff;
            }

            QPushButton#navActive {
                background: #184e4a;
                color: #ffffff;
                font-weight: 700;
            }

            QFrame#accountPanel {
                background: #172033;
                border-radius: 8px;
            }

            QLabel#accountLabel {
                color: #98a2b3;
                font-size: 11px;
            }

            QLabel#accountValue {
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
            }

            QWidget#workspace {
                background: #eef2f6;
            }

            QFrame#topbar,
            QFrame#heroPanel,
            QFrame#moduleCard {
                background: #ffffff;
                border: 1px solid #d9e0ea;
                border-radius: 8px;
            }

            QLabel#pageTitle {
                font-size: 22px;
                font-weight: 700;
                color: #101828;
            }

            QLabel#pageMeta,
            QLabel#heroBody,
            QLabel#cardDescription {
                color: #667085;
                font-size: 12px;
            }

            QLabel#eyebrow {
                color: #0f766e;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
            }

            QLabel#heroTitle {
                color: #101828;
                font-size: 20px;
                font-weight: 700;
            }

            QFrame#metricPill {
                background: #f1f5f9;
                border-radius: 7px;
            }

            QLabel#metricLabel {
                color: #667085;
                font-size: 10px;
            }

            QLabel#metricValue {
                color: #101828;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#cardTitle {
                color: #101828;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#statusBadge {
                background: #eef8f7;
                color: #115e59;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 700;
            }

            QPushButton#primaryButton {
                background: #0f766e;
                color: #ffffff;
                border: 0;
                border-radius: 7px;
                padding: 9px 15px;
                font-weight: 700;
            }

            QPushButton#primaryButton:hover {
                background: #115e59;
            }

            QPushButton#ghostButton {
                background: #f7f9fc;
                color: #101828;
                border: 1px solid #d9e0ea;
                border-radius: 7px;
                padding: 8px 14px;
            }

            QPushButton#ghostButton:hover {
                background: #edf2f7;
            }
            """
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = SamsAccountingWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
