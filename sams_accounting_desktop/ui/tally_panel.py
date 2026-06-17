from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QVBoxLayout,
)

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.ui.components import AppButton
from sams_accounting_desktop.workers.tally_worker import TallyWorker


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
