import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "Sam's Accounting Desktop"
APP_VERSION = "v1.0.1"
DEFAULT_TALLY_URL = "http://127.0.0.1:9000"
TIMEOUT_SECONDS = 8

COMPANY_PROBE_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>Company</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="Company">
            <TYPE>Company</TYPE>
            <FETCH>Name</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

LEDGERS_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>List of Ledgers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="List of Ledgers" ISMODIFY="No">
            <TYPE>Ledger</TYPE>
            <NATIVEMETHOD>Name</NATIVEMETHOD>
            <NATIVEMETHOD>Parent</NATIVEMETHOD>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""


@dataclass(frozen=True)
class Module:
    title: str
    subtitle: str
    metric: str
    state: str
    accent: str
    initials: str


@dataclass(frozen=True)
class Activity:
    time: str
    module: str
    description: str
    status: str


MODULES = [
    Module(
        "Tally",
        "Localhost Tally Prime connection, company aur masters fetch karein.",
        "Ready",
        "Connected",
        "#0f766e",
        "TA",
    ),
    Module(
        "Excel",
        "Excel bank rows review karein, ledgers fill karein, phir Tally me import karein.",
        "0 files",
        "Waiting",
        "#2563eb",
        "XL",
    ),
    Module(
        "Bank PDF",
        "Statement parse karke Payment/Receipt vouchers direct Tally me bhejein.",
        "Parser",
        "Available",
        "#7c3aed",
        "BP",
    ),
    Module(
        "Image PDF",
        "Scanned statement parse karke ledger mapping ke saath Tally posting karein.",
        "OCR",
        "Available",
        "#c2410c",
        "IP",
    ),
    Module(
        "Purchase Reco",
        "GST portal purchase Excel ko Tally purchase vouchers ke saath reconcile karein.",
        "GST",
        "Multi-file",
        "#15803d",
        "PR",
    ),
    Module(
        "Sales",
        "Random sales invoice preview generate karke direct Tally me create karein.",
        "Invoice",
        "Generator",
        "#be123c",
        "SA",
    ),
    Module(
        "Voucher Entry",
        "Journal, Payment, Receipt, Purchase/Sales ya custom 2-ledger voucher add karein.",
        "Manual",
        "Entry",
        "#334155",
        "VE",
    ),
]


ACTIVITY = [
    Activity("Today", "Tally", "Company and masters sync ready", "Healthy"),
    Activity("Today", "Purchase Reco", "Multiple GST Excel support enabled", "Ready"),
    Activity("Today", "Bank PDF", "Payment and Receipt posting workflow available", "Ready"),
    Activity("Today", "Sales", "Invoice preview generator available", "Ready"),
]


def make_icon(text: str, color: str, size: int = 38, radius: int = 9) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", max(9, size // 4), QFont.Weight.DemiBold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()

    return QIcon(pixmap)


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].upper()


def post_tally_xml(tally_url: str, xml: str) -> str:
    request = urllib.request.Request(
        tally_url.rstrip("/"),
        data=xml.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "User-Agent": "SamsAccountingDesktop/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_company_names(raw_response: str) -> list[str]:
    try:
        root = ET.fromstring(raw_response)
    except ET.ParseError:
        return []

    companies: list[str] = []
    seen: set[str] = set()
    for element in root.iter():
        if tag_name(element) not in {"COMPANY", "NAME", "CMPNAME"}:
            continue
        name = clean_text(element.attrib.get("NAME") or element.text)
        if name and name not in seen:
            seen.add(name)
            companies.append(name)
    return companies


def parse_ledgers(raw_response: str, query: str = "") -> list[str]:
    root = ET.fromstring(raw_response)
    ledgers: list[str] = []
    seen: set[str] = set()

    for element in root.iter():
        if tag_name(element) != "LEDGER":
            continue
        name = clean_text(element.attrib.get("NAME"))
        if not name:
            for child in element:
                if tag_name(child) == "NAME":
                    name = clean_text(child.text)
                    break
        if name and name not in seen:
            seen.add(name)
            ledgers.append(name)

    if not ledgers:
        for element in root.iter():
            if tag_name(element) in {"DSPDISPNAME", "DSPACCNAME", "LEDGERNAME", "NAME"}:
                name = clean_text(element.text)
                if name and name not in seen:
                    seen.add(name)
                    ledgers.append(name)

    needle = query.strip().lower()
    if needle:
        ledgers = [ledger for ledger in ledgers if needle in ledger.lower()]
    return ledgers


def test_tally_connection(tally_url: str) -> tuple[bool, str, list[str]]:
    try:
        response = post_tally_xml(tally_url, COMPANY_PROBE_XML)
    except urllib.error.URLError as exc:
        return False, f"Tally not reachable at {tally_url}: {exc.reason}", []
    except TimeoutError:
        return False, f"Tally timed out at {tally_url}", []

    if "<LINEERROR>" in response.upper():
        return False, "Tally responded, but returned an XML line error.", []

    companies = parse_company_names(response)
    if companies:
        return True, f"Tally connected. Active company: {companies[0]}", companies
    if "ENVELOPE" in response.upper() or "COMPANY" in response.upper():
        return True, f"Tally connected at {tally_url}", []
    return True, f"Tally responded at {tally_url}", []


def fetch_tally_ledgers(tally_url: str, query: str = "") -> list[str]:
    response = post_tally_xml(tally_url, LEDGERS_XML)
    if "<LINEERROR>" in response.upper():
        raise RuntimeError("Tally returned an XML line error while fetching ledgers.")
    return parse_ledgers(response, query=query)


class TallyWorker(QThread):
    finished = Signal(str, bool, str, object)

    def __init__(self, action: str, tally_url: str, query: str = ""):
        super().__init__()
        self.action = action
        self.tally_url = tally_url
        self.query = query

    def run(self):
        try:
            if self.action == "test":
                ok, message, companies = test_tally_connection(self.tally_url)
                self.finished.emit(self.action, ok, message, companies)
            elif self.action == "ledgers":
                ledgers = fetch_tally_ledgers(self.tally_url, self.query)
                self.finished.emit(self.action, True, f"Fetched {len(ledgers)} ledgers from Tally.", ledgers)
            else:
                self.finished.emit(self.action, False, f"Unknown action: {self.action}", [])
        except Exception as exc:
            self.finished.emit(self.action, False, str(exc), [])


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


class TallyConnectorPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("sidePanel")
        self.worker: TallyWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Tally Connector")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.status_label = QLabel("Not tested")
        self.status_label.setObjectName("connectorStatusIdle")
        layout.addWidget(self.status_label)

        url_label = QLabel("Tally HTTP URL")
        url_label.setObjectName("mutedLabel")
        layout.addWidget(url_label)

        self.url_input = QLineEdit(DEFAULT_TALLY_URL)
        self.url_input.setObjectName("searchBox")
        layout.addWidget(self.url_input)

        connect_row = QHBoxLayout()
        self.test_button = AppButton("Test Connection", "primary")
        self.test_button.clicked.connect(self.test_connection)
        self.fetch_button = AppButton("Fetch Ledgers", "secondary")
        self.fetch_button.clicked.connect(self.fetch_ledgers)
        connect_row.addWidget(self.test_button)
        connect_row.addWidget(self.fetch_button)
        layout.addLayout(connect_row)

        query_label = QLabel("Ledger search")
        query_label.setObjectName("mutedLabel")
        layout.addWidget(query_label)

        self.query_input = QLineEdit()
        self.query_input.setObjectName("searchBox")
        self.query_input.setPlaceholderText("Example: sales, cash, bank")
        layout.addWidget(self.query_input)

        self.company_label = QLabel("Company: -")
        self.company_label.setObjectName("healthValue")
        layout.addWidget(self.company_label)

        ledgers_title = QLabel("Ledgers")
        ledgers_title.setObjectName("sectionTitle")
        layout.addWidget(ledgers_title)

        self.ledger_list = QListWidget()
        self.ledger_list.setObjectName("ledgerList")
        self.ledger_list.setMinimumHeight(170)
        layout.addWidget(self.ledger_list)

        log_title = QLabel("Connector log")
        log_title.setObjectName("sectionTitle")
        layout.addWidget(log_title)

        self.log = QPlainTextEdit()
        self.log.setObjectName("connectorLog")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(80)
        self.log.setPlainText(
            "Tally Prime me HTTP server port 9000 enable karein, company open rakhein, phir Test Connection dabayein."
        )
        layout.addWidget(self.log)

    def tally_url(self) -> str:
        return self.url_input.text().strip().rstrip("/") or DEFAULT_TALLY_URL

    def set_busy(self, busy: bool):
        self.test_button.setEnabled(not busy)
        self.fetch_button.setEnabled(not busy)
        if busy:
            self.status_label.setText("Working...")
            self.status_label.setObjectName("connectorStatusIdle")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)

    def append_log(self, message: str):
        self.log.appendPlainText(message)

    def test_connection(self):
        self.start_worker("test")

    def fetch_ledgers(self):
        self.start_worker("ledgers", query=self.query_input.text())

    def start_worker(self, action: str, query: str = ""):
        if self.worker and self.worker.isRunning():
            return
        self.set_busy(True)
        self.append_log(f"> {action} {self.tally_url()}")
        self.worker = TallyWorker(action, self.tally_url(), query=query)
        self.worker.finished.connect(self.handle_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def handle_worker_finished(self, action: str, ok: bool, message: str, payload: object):
        self.set_busy(False)
        self.status_label.setText("Connected" if ok else "Failed")
        self.status_label.setObjectName("connectorStatusOk" if ok else "connectorStatusError")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.append_log(("OK: " if ok else "ERROR: ") + message)

        if action == "test" and ok:
            companies = payload if isinstance(payload, list) else []
            self.company_label.setText(f"Company: {companies[0]}" if companies else "Company: Tally responded")
        elif action == "ledgers" and ok:
            ledgers = payload if isinstance(payload, list) else []
            self.ledger_list.clear()
            self.ledger_list.addItems(ledgers[:200])


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
        self.setStyleSheet(
            """
            QWidget#shell,
            QWidget#workspace {
                background: #eef2f6;
                color: #101828;
                font-family: Segoe UI;
            }

            QScrollArea#workspaceScroll {
                background: #eef2f6;
            }

            QFrame#sidebar {
                background: #101828;
            }

            QLabel#brandTitle {
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
            }

            QLabel#brandDetail,
            QLabel#userPlan {
                color: #98a2b3;
                font-size: 11px;
            }

            QPushButton#navItem,
            QPushButton#navActive {
                border: 0;
                border-radius: 7px;
                color: #d0d5dd;
                background: transparent;
                text-align: left;
                padding: 7px 12px;
                font-size: 13px;
            }

            QPushButton#navItem:hover {
                background: #1d2939;
                color: #ffffff;
            }

            QPushButton#navActive {
                background: #184e4a;
                color: #ffffff;
                font-weight: 700;
            }

            QFrame#userCard {
                background: #172033;
                border-radius: 8px;
            }

            QLabel#userName {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
            }

            QFrame#topbar,
            QFrame#hero,
            QFrame#kpiCard,
            QFrame#moduleCard,
            QFrame#sidePanel,
            QFrame#activityPanel {
                background: #ffffff;
                border: 1px solid #d9e0ea;
                border-radius: 8px;
            }

            QLabel#pageTitle {
                color: #101828;
                font-size: 22px;
                font-weight: 700;
            }

            QLabel#pageSubtitle,
            QLabel#heroBody,
            QLabel#cardBody,
            QLabel#smallText,
            QLabel.smallText {
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

            QLabel#mutedLabel,
            QLabel#stateText {
                color: #667085;
                font-size: 11px;
            }

            QLabel#kpiValue {
                color: #101828;
                font-size: 22px;
                font-weight: 700;
            }

            QLabel#cardTitle {
                color: #101828;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#sectionTitle {
                color: #101828;
                font-size: 15px;
                font-weight: 700;
            }

            QLabel#badge {
                background: #eef8f7;
                color: #115e59;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 700;
            }

            QLabel#healthValue {
                color: #101828;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#connectorStatusIdle,
            QLabel#connectorStatusOk,
            QLabel#connectorStatusError {
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#connectorStatusIdle {
                background: #f1f5f9;
                color: #475467;
            }

            QLabel#connectorStatusOk {
                background: #ecfdf3;
                color: #067647;
            }

            QLabel#connectorStatusError {
                background: #fef3f2;
                color: #b42318;
            }

            QLineEdit#searchBox {
                background: #f8fafc;
                border: 1px solid #d9e0ea;
                border-radius: 7px;
                padding: 9px 12px;
                color: #101828;
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

            QPushButton#secondaryButton {
                background: #f7f9fc;
                color: #101828;
                border: 1px solid #d9e0ea;
                border-radius: 7px;
                padding: 8px 14px;
                font-weight: 600;
            }

            QPushButton#secondaryButton:hover {
                background: #edf2f7;
            }

            QProgressBar#healthProgress {
                height: 8px;
                background: #edf2f7;
                border: 0;
                border-radius: 4px;
            }

            QProgressBar#healthProgress::chunk {
                background: #0f766e;
                border-radius: 4px;
            }

            QListWidget#ledgerList {
                background: #f8fafc;
                border: 1px solid #d9e0ea;
                border-radius: 7px;
                padding: 6px;
                color: #101828;
                font-size: 12px;
            }

            QListWidget#ledgerList::item {
                padding: 7px;
                border-radius: 5px;
            }

            QListWidget#ledgerList::item:selected {
                background: #d9f3ef;
                color: #101828;
            }

            QPlainTextEdit#connectorLog {
                background: #101828;
                color: #d0d5dd;
                border: 0;
                border-radius: 7px;
                padding: 9px;
                font-family: Consolas;
                font-size: 11px;
            }

            QTableWidget#activityTable {
                border: 0;
                background: #ffffff;
                color: #101828;
                gridline-color: transparent;
                selection-background-color: transparent;
                font-size: 12px;
            }

            QHeaderView::section {
                background: #f8fafc;
                color: #475467;
                border: 0;
                border-bottom: 1px solid #d9e0ea;
                padding: 8px;
                font-weight: 700;
            }
            """
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    window = DashboardWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
