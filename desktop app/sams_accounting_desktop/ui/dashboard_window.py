from PySide6.QtCore import QDateTime, QEvent, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import APP_NAME, APP_VERSION, DEFAULT_TALLY_URL
from sams_accounting_desktop.data import MODULES
from sams_accounting_desktop.ui.components import AppButton, ModuleCard, NavItem, StatusChip
from sams_accounting_desktop.ui.icons import logo_icon, logo_pixmap
from sams_accounting_desktop.ui.bank_pdf_panel import BankPdfPanel
from sams_accounting_desktop.ui.purchase_reco_panel import PurchaseRecoPanel
from sams_accounting_desktop.ui.sales_panel import SalesChoicePanel
from sams_accounting_desktop.ui.styles import STYLESHEET
from sams_accounting_desktop.ui.tally_panel import TallyConnectorPanel
from sams_accounting_desktop.workers.tally_worker import TallyWorker


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(logo_icon(64))
        self.setMinimumSize(1180, 700)
        self.resize(1320, 820)
        self.nav_buttons: dict[str, NavItem] = {}
        self.tally_status_worker: TallyWorker | None = None
        self.tally_status_state = "checking"
        self.current_view = "Dashboard"
        self.view_history: list[str] = []
        self.back_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.back_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.back_shortcut.activated.connect(self.go_back)
        QApplication.instance().installEventFilter(self)

        shell = QWidget()
        self.shell = shell
        shell.setObjectName("shell")
        root = QVBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.navbar_widget = self.top_navigation()
        root.addWidget(self.navbar_widget)
        self.workspace_scroll = self.workspace()
        root.addWidget(self.workspace_scroll, 1)

        self.setCentralWidget(shell)
        self.apply_styles()
        self.start_tally_status_monitor()

    def top_navigation(self) -> QWidget:
        navbar = QFrame()
        navbar.setObjectName("topNav")
        navbar.setFixedHeight(78)

        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(14)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(42))
        brand.addWidget(logo)

        brand_copy = QWidget()
        copy = QVBoxLayout(brand_copy)
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        name = QLabel("Sams Accounting")
        name.setObjectName("brandTitle")
        detail = QLabel("Desktop workspace")
        detail.setObjectName("brandDetail")
        copy.addWidget(name)
        copy.addWidget(detail)
        brand.addWidget(brand_copy)
        layout.addLayout(brand)

        nav_strip = QWidget()
        nav_strip.setObjectName("navStrip")
        nav_layout = QHBoxLayout(nav_strip)
        nav_layout.setContentsMargins(8, 0, 8, 0)
        nav_layout.setSpacing(6)

        desktop_button = NavItem("Desktop", "DA", active=True)
        desktop_button.setMinimumHeight(42)
        desktop_button.setMinimumWidth(112)
        desktop_button.clicked.connect(lambda: self.open_view("Dashboard"))
        self.nav_buttons["Dashboard"] = desktop_button
        nav_layout.addWidget(desktop_button)

        nav_layout.addStretch()
        layout.addWidget(nav_strip, 1)

        self.tally_status_button = QPushButton("Tally checking\nConnecting…")
        self.tally_status_button.setObjectName("tallyStatusChecking")
        self.tally_status_button.setMinimumHeight(48)
        self.tally_status_button.setMinimumWidth(214)
        self.tally_status_button.setToolTip("Click to open Tally connector")
        self.tally_status_button.clicked.connect(self.open_tally_from_status)
        layout.addWidget(self.tally_status_button)

        return navbar

    def start_tally_status_monitor(self):
        self.tally_status_timer = QTimer(self)
        self.tally_status_timer.setInterval(15000)
        self.tally_status_timer.timeout.connect(self.refresh_tally_status)
        self.tally_status_timer.start()
        QTimer.singleShot(250, self.refresh_tally_status)

    def open_tally_from_status(self):
        self.open_view("Tally")
        self.refresh_tally_status()

    def refresh_tally_status(self):
        if self.tally_status_worker and self.tally_status_worker.isRunning():
            return
        if self.tally_status_state == "checking":
            self.update_tally_status_button("Tally checking\nConnecting…", "checking")
        worker = TallyWorker("test", DEFAULT_TALLY_URL)
        self.tally_status_worker = worker
        worker.finished.connect(self.handle_tally_status_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def handle_tally_status_finished(self, _action: str, ok: bool, message: str, payload: object):
        checked_at = QDateTime.currentDateTime().toString("h:mm AP")
        companies = payload if ok and isinstance(payload, list) else []
        detail = companies[0] if companies else ("Available" if ok else "Retry available")
        text = f"Tally connected\n{detail} · {checked_at}" if ok else f"Tally offline\n{detail} · {checked_at}"
        state = "connected" if ok else "disconnected"
        self.update_tally_status_button(text, state, message)
        self.tally_status_worker = None

    def update_tally_status_button(self, text: str, state: str, message: str = ""):
        self.tally_status_state = state
        self.tally_status_button.setText(text)
        object_name = {
            "connected": "tallyStatusConnected",
            "disconnected": "tallyStatusDisconnected",
        }.get(state, "tallyStatusChecking")
        self.tally_status_button.setObjectName(object_name)
        tooltip = "Click to open Tally connector"
        if message:
            tooltip = f"{message}\n{tooltip}"
        self.tally_status_button.setToolTip(tooltip)
        self.tally_status_button.style().unpolish(self.tally_status_button)
        self.tally_status_button.style().polish(self.tally_status_button)

    def stop_tally_status_monitor(self):
        if hasattr(self, "tally_status_timer"):
            self.tally_status_timer.stop()
        if self.tally_status_worker and self.tally_status_worker.isRunning():
            self.tally_status_worker.wait(9000)

    def closeEvent(self, event):
        self.stop_tally_status_monitor()
        super().closeEvent(event)

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
        layout.setContentsMargins(28, 18, 28, 20)
        layout.setSpacing(12)

        layout.addWidget(self.topbar())
        layout.addLayout(self.module_grid())
        return page

    def topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(72)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Select a workflow")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Review, reconcile, and post accounting data with confidence.")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack)

        layout.addStretch()

        return topbar

    def module_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        for col in range(2):
            grid.setColumnStretch(col, 1)

        for index, module in enumerate(MODULES):
            card = ModuleCard(module)
            card.open_requested.connect(self.open_module)
            grid.addWidget(card, index // 2, index % 2)

        return grid

    def open_module(self, module_name: str):
        self.open_view(module_name)

    def open_view(self, view_name: str, remember: bool = True):
        if remember and view_name != self.current_view:
            self.view_history.append(self.current_view)

        if view_name in {"Purchase Reco", "Purchase Reconciliation"}:
            self.current_view = "Purchase Reconciliation"
            self.set_nav_active("Purchase Reconciliation")
            self.workspace_scroll.setWidget(PurchaseRecoPanel())
            return
        if view_name == "Tally":
            self.current_view = "Tally"
            self.set_nav_active("Tally")
            self.workspace_scroll.setWidget(self.tool_page("Tally Connector", TallyConnectorPanel()))
            return
        if view_name == "Sales":
            self.current_view = "Sales"
            self.set_nav_active("Sales")
            self.workspace_scroll.setWidget(SalesChoicePanel())
            return
        if view_name == "Bank PDF":
            self.current_view = "Bank PDF"
            self.set_nav_active("Bank PDF")
            self.workspace_scroll.setWidget(BankPdfPanel())
            return
        if view_name == "Dashboard":
            self.current_view = "Dashboard"
            self.set_nav_active("Dashboard")
            self.workspace_scroll.setWidget(self.dashboard_page())
            return
        module = self.module_by_name(view_name)
        if module is not None:
            self.current_view = module.title
            self.set_nav_active(view_name)
            self.workspace_scroll.setWidget(self.tool_page(f"{module.title} Workflow", self.pending_module_panel(module)))

    def go_back(self):
        if not self.view_history:
            return
        previous_view = self.view_history.pop()
        self.open_view(previous_view, remember=False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
            event.accept()
            return
        if self.handle_keyboard_navigation(event):
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            if self.handle_keyboard_navigation(event):
                return True
        return super().eventFilter(watched, event)

    def handle_keyboard_navigation(self, event) -> bool:
        key = event.key()
        focus = QApplication.focusWidget()
        editable_widgets = (QLineEdit, QPlainTextEdit, QListWidget, QTableWidget)

        if key in {Qt.Key.Key_Return, Qt.Key.Key_Enter} and isinstance(focus, QAbstractButton):
            focus.click()
            event.accept()
            return True

        if key not in {Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down}:
            return False

        if isinstance(focus, editable_widgets):
            return False

        move_forward = key in {Qt.Key.Key_Right, Qt.Key.Key_Down}
        self.focusNextPrevChild(move_forward)
        event.accept()
        return True

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

    def pending_module_panel(self, module) -> QWidget:
        panel = QFrame()
        panel.setObjectName("sidePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        badge = StatusChip("Setup pending", "warning")
        title = QLabel(module.title)
        title.setObjectName("sectionTitle")
        body = QLabel(module.subtitle)
        body.setObjectName("cardBody")
        body.setWordWrap(True)
        note = QLabel("Is workflow ki full screen abhi app build me connected nahi hai.")
        note.setObjectName("smallText")
        note.setWordWrap(True)
        back_button = AppButton("Back to Desktop", "secondary", "DA", "#0f766e")
        back_button.clicked.connect(lambda: self.open_view("Dashboard"))

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(note)
        layout.addWidget(back_button)
        layout.addStretch()
        return panel

    def module_by_name(self, module_name: str):
        return next((module for module in MODULES if module.title == module_name), None)

    def set_nav_active(self, active_name: str):
        for name, button in self.nav_buttons.items():
            button.set_active(name == active_name)

    def apply_styles(self):
        self.setStyleSheet(STYLESHEET)
