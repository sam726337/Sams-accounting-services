from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import APP_NAME, APP_VERSION
from sams_accounting_desktop.data import MODULES
from sams_accounting_desktop.ui.components import ActivityTable, AppButton, KpiCard, ModuleCard, NavItem
from sams_accounting_desktop.ui.icons import make_icon
from sams_accounting_desktop.ui.styles import STYLESHEET
from sams_accounting_desktop.ui.tally_panel import TallyConnectorPanel


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(make_icon("SA", "#0f766e", 64))
        self.setMinimumSize(1180, 740)
        self.resize(1320, 820)

        shell = QWidget()
        shell.setObjectName("shell")
        root = QHBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self.sidebar())
        root.addWidget(self.workspace(), 1)

        self.setCentralWidget(shell)
        self.apply_styles()

    def sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(272)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 18)
        layout.setSpacing(8)

        brand = QHBoxLayout()
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(make_icon("SA", "#14b8a6", 44, 10).pixmap(44, 44))
        brand.addWidget(logo)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        name = QLabel("Sam's Accounting")
        name.setObjectName("brandTitle")
        detail = QLabel("Automation workspace")
        detail.setObjectName("brandDetail")
        copy.addWidget(name)
        copy.addWidget(detail)
        brand.addLayout(copy)
        layout.addLayout(brand)
        layout.addSpacing(18)

        nav = [
            ("Dashboard", "DA"),
            ("Tally", "TA"),
            ("Excel", "XL"),
            ("Bank PDF", "BP"),
            ("Image PDF", "IP"),
            ("Purchase Reco", "PR"),
            ("Sales", "SA"),
            ("Voucher Entry", "VE"),
        ]
        for index, (label, initials) in enumerate(nav):
            layout.addWidget(NavItem(label, initials, active=index == 0))

        layout.addStretch()

        user = QFrame()
        user.setObjectName("userCard")
        user_layout = QVBoxLayout(user)
        user_layout.setContentsMargins(14, 13, 14, 13)
        user_layout.setSpacing(4)
        account = QLabel("sameer mansuri")
        account.setObjectName("userName")
        plan = QLabel("Verified subscription")
        plan.setObjectName("userPlan")
        user_layout.addWidget(account)
        user_layout.addWidget(plan)
        layout.addWidget(user)

        return sidebar

    def workspace(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("workspaceScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        page.setObjectName("workspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(self.topbar())
        layout.addWidget(self.hero())
        layout.addLayout(self.kpis())

        middle = QHBoxLayout()
        middle.setSpacing(18)
        middle.addLayout(self.module_grid(), 3)
        middle.addWidget(TallyConnectorPanel(), 1)
        layout.addLayout(middle)
        layout.addWidget(ActivityTable())

        scroll.setWidget(page)
        return scroll

    def topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setMinimumHeight(76)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Logged in: sameer mansuri | Subscription: Verified | AI credit: Rs 500.0000")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack)

        layout.addStretch()

        search = QLineEdit()
        search.setObjectName("searchBox")
        search.setPlaceholderText("Search module or workflow")
        search.setFixedWidth(260)
        layout.addWidget(search)
        layout.addWidget(AppButton("Check Tally", "secondary"))
        layout.addWidget(AppButton("New Voucher", "primary"))

        return topbar

    def hero(self) -> QWidget:
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(142)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(24, 20, 22, 20)
        layout.setSpacing(18)

        copy = QVBoxLayout()
        copy.setSpacing(5)
        eyebrow = QLabel("Desktop SaaS control center")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Accounting operations, Tally posting, and GST reconciliation in one workspace")
        title.setObjectName("heroTitle")
        title.setWordWrap(True)
        body = QLabel("Designed for office accounting work where PDF, Excel, GST data, and Tally Prime need to move together.")
        body.setObjectName("heroBody")
        body.setWordWrap(True)
        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(body)
        layout.addLayout(copy, 1)

        action_stack = QVBoxLayout()
        action_stack.setSpacing(9)
        action_stack.addWidget(AppButton("Start Bank Parsing", "primary"))
        action_stack.addWidget(AppButton("Run Purchase Reco", "secondary"))
        action_stack.addWidget(AppButton("Open Sales Generator", "secondary"))
        layout.addLayout(action_stack)

        return hero

    def kpis(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(KpiCard("Tally status", "Connected", "Localhost company data ready", "#0f766e"))
        row.addWidget(KpiCard("Pending imports", "0", "No files waiting in queue", "#2563eb"))
        row.addWidget(KpiCard("Reco mode", "All-quarter", "Multiple GST Excel files supported", "#15803d"))
        row.addWidget(KpiCard("Backup", "Optional", "CSV backup available before posting", "#475467"))
        return row

    def module_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        for col in range(2):
            grid.setColumnStretch(col, 1)

        for index, module in enumerate(MODULES):
            grid.addWidget(ModuleCard(module), index // 2, index % 2)

        return grid

    def apply_styles(self):
        self.setStyleSheet(STYLESHEET)
