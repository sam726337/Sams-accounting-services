from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import APP_NAME, APP_VERSION
from sams_accounting_desktop.data import MODULES
from sams_accounting_desktop.ui.components import ActivityTable, AppButton, InsightCard, KpiCard, ModuleCard, NavItem, StatusChip
from sams_accounting_desktop.ui.icons import logo_icon, logo_pixmap, make_menu_icon
from sams_accounting_desktop.ui.purchase_reco_panel import PurchaseRecoPanel
from sams_accounting_desktop.ui.styles import STYLESHEET
from sams_accounting_desktop.ui.tally_panel import TallyConnectorPanel


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(logo_icon(64))
        self.setMinimumSize(1180, 740)
        self.resize(1320, 820)
        self.nav_buttons: dict[str, NavItem] = {}
        self.sidebar_collapsed = False

        shell = QWidget()
        self.shell = shell
        shell.setObjectName("shell")
        root = QHBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar_widget = self.sidebar()
        root.addWidget(self.sidebar_widget)
        self.workspace_scroll = self.workspace()
        root.addWidget(self.workspace_scroll, 1)

        self.setCentralWidget(shell)
        self.apply_styles()
        self.create_floating_nav_button()

    def sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(272)

        layout = QVBoxLayout(sidebar)
        self.sidebar_layout = layout
        layout.setContentsMargins(16, 78, 16, 18)
        layout.setSpacing(8)

        brand = QHBoxLayout()
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(46))
        brand.addWidget(logo)

        brand_copy = QWidget()
        copy = QVBoxLayout(brand_copy)
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        name = QLabel("Sam's Accounting")
        name.setObjectName("brandTitle")
        detail = QLabel("Automation workspace")
        detail.setObjectName("brandDetail")
        copy.addWidget(name)
        copy.addWidget(detail)
        self.brand_copy_widget = brand_copy
        brand.addWidget(brand_copy)
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
            button = NavItem(label, initials, active=index == 0)
            button.clicked.connect(lambda _checked=False, name=label: self.open_view(name))
            self.nav_buttons[label] = button
            layout.addWidget(button)

        layout.addStretch()

        user = QFrame()
        self.user_card = user
        user.setObjectName("userCard")
        user_layout = QVBoxLayout(user)
        user_layout.setContentsMargins(14, 13, 14, 13)
        user_layout.setSpacing(4)
        account = QLabel("sameer mansuri")
        account.setObjectName("userName")
        plan = QLabel("License verified")
        plan.setObjectName("userPlan")
        user_layout.addWidget(account)
        user_layout.addWidget(plan)
        layout.addWidget(user)

        return sidebar

    def create_floating_nav_button(self):
        self.floating_nav_button = QPushButton(self.shell)
        self.floating_nav_button.setObjectName("hamburgerButton")
        self.floating_nav_button.setIcon(make_menu_icon(28, "#0f766e"))
        self.floating_nav_button.setFixedSize(46, 46)
        self.floating_nav_button.setToolTip("Collapse navigation")
        self.floating_nav_button.clicked.connect(self.toggle_sidebar)
        self.update_floating_nav_position()

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.apply_sidebar_state()

    def apply_sidebar_state(self):
        width = 84 if self.sidebar_collapsed else 272
        self.sidebar_widget.setFixedWidth(width)
        self.sidebar_layout.setContentsMargins(12 if self.sidebar_collapsed else 16, 78, 12 if self.sidebar_collapsed else 16, 18)
        self.brand_copy_widget.setVisible(not self.sidebar_collapsed)
        self.user_card.setVisible(not self.sidebar_collapsed)
        self.floating_nav_button.setToolTip("Expand navigation" if self.sidebar_collapsed else "Collapse navigation")
        for button in self.nav_buttons.values():
            button.set_compact(self.sidebar_collapsed)
            button.set_active(button.isChecked())
        self.update_floating_nav_position()

    def update_floating_nav_position(self):
        if not hasattr(self, "floating_nav_button"):
            return
        self.floating_nav_button.move(18, 18)
        self.floating_nav_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_floating_nav_position()

    def workspace(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("workspaceScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.dashboard_page())
        return scroll

    def dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("workspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(self.topbar())
        layout.addLayout(self.health_strip())
        layout.addWidget(self.hero())
        layout.addLayout(self.kpis())

        middle = QHBoxLayout()
        middle.setSpacing(18)
        middle.addLayout(self.module_grid(), 3)
        middle.addWidget(TallyConnectorPanel(), 1)
        layout.addLayout(middle)
        layout.addWidget(ActivityTable())
        return page

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
        layout.addWidget(StatusChip("Live workspace", "ok"))
        check_tally = AppButton("Check Tally", "secondary", "TA", "#0f766e")
        check_tally.clicked.connect(lambda: self.open_view("Tally"))
        layout.addWidget(check_tally)
        layout.addWidget(AppButton("New Voucher", "primary", "VE", "#115e59"))

        return topbar

    def health_strip(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(InsightCard("Tally gateway", "Localhost:9000", "Ready for company sync", "#0f766e", "TG"))
        row.addWidget(InsightCard("License", "Verified", "Desktop access active", "#2563eb", "LC"))
        row.addWidget(InsightCard("Release", APP_VERSION, "Update manifest enabled", "#7c3aed", "UP"))
        row.addWidget(InsightCard("AI credit", "Rs 500.0000", "Available for assisted workflows", "#b54708", "AI"))
        return row

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
        action_stack.addWidget(AppButton("Start Bank Parsing", "primary", "BP", "#0f766e"))
        purchase_button = AppButton("Run Purchase Reco", "secondary", "PR", "#15803d")
        purchase_button.clicked.connect(lambda: self.open_view("Purchase Reco"))
        action_stack.addWidget(purchase_button)
        action_stack.addWidget(AppButton("Open Sales Generator", "secondary", "SA", "#be123c"))
        layout.addLayout(action_stack)

        return hero

    def kpis(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(KpiCard("Tally status", "Ready", "Localhost company data ready", "#0f766e"))
        row.addWidget(KpiCard("Pending imports", "0", "No files waiting in queue", "#2563eb"))
        row.addWidget(KpiCard("Reco mode", "Multi-file", "Multiple GST Excel files supported", "#15803d"))
        row.addWidget(KpiCard("Review queue", "0", "Probable matches waiting", "#b54708"))
        return row

    def module_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        for col in range(2):
            grid.setColumnStretch(col, 1)

        for index, module in enumerate(MODULES):
            card = ModuleCard(module)
            card.open_requested.connect(self.open_module)
            grid.addWidget(card, index // 2, index % 2)

        return grid

    def open_module(self, module_name: str):
        if module_name == "Purchase Reco":
            self.open_view("Purchase Reco")
            return
        if module_name == "Tally":
            self.open_view("Tally")

    def open_view(self, view_name: str):
        if view_name == "Purchase Reco":
            self.set_nav_active("Purchase Reco")
            self.workspace_scroll.setWidget(PurchaseRecoPanel())
            return
        if view_name == "Tally":
            self.set_nav_active("Tally")
            self.workspace_scroll.setWidget(self.tool_page("Tally Connector", TallyConnectorPanel()))
            return
        if view_name == "Dashboard":
            self.set_nav_active("Dashboard")
            self.workspace_scroll.setWidget(self.dashboard_page())

    def tool_page(self, title: str, widget: QWidget) -> QWidget:
        page = QWidget()
        page.setObjectName("workspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 12, 22, 12)
        title_stack = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        subheading = QLabel("Local desktop workflow")
        subheading.setObjectName("pageSubtitle")
        title_stack.addWidget(heading)
        title_stack.addWidget(subheading)
        header_layout.addLayout(title_stack)
        header_layout.addStretch()
        header_layout.addWidget(StatusChip("Ready", "info"))

        layout.addWidget(header)
        layout.addWidget(widget)
        layout.addStretch()
        return page

    def set_nav_active(self, active_name: str):
        for name, button in self.nav_buttons.items():
            button.set_active(name == active_name)

    def apply_styles(self):
        self.setStyleSheet(STYLESHEET)
