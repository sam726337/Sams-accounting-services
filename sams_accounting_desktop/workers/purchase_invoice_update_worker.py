from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QThread, Signal

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.purchase_reco_service import update_purchase_invoice_numbers_same_as_excel


class PurchaseInvoiceSameAsExcelWorker(QThread):
    progress = Signal(int, int)
    completed = Signal(bool, str, object)

    def __init__(
        self,
        reconciliation_results: Sequence[dict],
        *,
        tally_url: str = DEFAULT_TALLY_URL,
    ):
        super().__init__()
        self.reconciliation_results = list(reconciliation_results)
        self.tally_url = tally_url

    def run(self):
        try:
            results = update_purchase_invoice_numbers_same_as_excel(
                self.reconciliation_results,
                tally_url=self.tally_url,
                progress_callback=self.progress.emit,
            )
            success_count = sum(1 for result in results if result.success)
            failure_count = len(results) - success_count
            message = f"{success_count} purchase bill number same as Excel updated. {failure_count} failed."
            self.completed.emit(failure_count == 0, message, results)
        except Exception as exc:
            self.completed.emit(False, str(exc), [])
