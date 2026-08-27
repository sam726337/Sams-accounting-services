from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QThread, Signal

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.purchase_reco_service import (
    LedgerGstSuggestion,
    build_missing_ledger_gst_suggestions,
    update_suggested_ledger_gstins,
)


class PurchaseLedgerGstScanWorker(QThread):
    finished = Signal(bool, str, object)

    def __init__(
        self,
        excel_paths: Sequence[str | Path],
        *,
        tally_url: str = DEFAULT_TALLY_URL,
    ):
        super().__init__()
        self.excel_paths = [str(path) for path in excel_paths]
        self.tally_url = tally_url

    def run(self):
        try:
            suggestions = build_missing_ledger_gst_suggestions(
                self.excel_paths,
                tally_url=self.tally_url,
            )
            suggested_count = sum(1 for suggestion in suggestions if suggestion.has_suggestion)
            message = (
                f"{len(suggestions)} debtors/creditors ledgers me GSTIN missing hai. "
                f"{suggested_count} Excel match suggestion ready."
            )
            self.finished.emit(True, message, suggestions)
        except Exception as exc:
            self.finished.emit(False, str(exc), [])


class PurchaseLedgerGstUpdateWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str, object)

    def __init__(
        self,
        suggestions: Sequence[LedgerGstSuggestion],
        *,
        tally_url: str = DEFAULT_TALLY_URL,
    ):
        super().__init__()
        self.suggestions = list(suggestions)
        self.tally_url = tally_url

    def run(self):
        try:
            results = update_suggested_ledger_gstins(
                self.suggestions,
                tally_url=self.tally_url,
                progress_callback=self.progress.emit,
            )
            success_count = sum(1 for result in results if result.success)
            failure_count = len(results) - success_count
            message = f"{success_count} ledger GSTIN updated. {failure_count} failed."
            self.finished.emit(failure_count == 0, message, results)
        except Exception as exc:
            self.finished.emit(False, str(exc), [])
