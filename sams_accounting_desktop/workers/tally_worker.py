from PySide6.QtCore import QThread, Signal

from sams_accounting_desktop.services.tally_client import fetch_tally_ledgers, test_tally_connection


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
