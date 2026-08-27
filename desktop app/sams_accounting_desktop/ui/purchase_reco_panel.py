from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.purchase_reco_service import (
    PurchaseRecoRun,
    export_purchase_reco_excel,
    export_purchase_reco_pdf,
)
from sams_accounting_desktop.services.purchase_export import (
    export_reconciliation_to_excel,
    export_reconciliation_to_pdf,
)
from sams_accounting_desktop.services.purchase_reconciliation import invoice_digit_suffixes, only_digits
from sams_accounting_desktop.ui.components import AppButton, KpiCard, StatusChip, WorkflowStepper
from sams_accounting_desktop.workers.purchase_gst_worker import (
    PurchaseLedgerGstScanWorker,
    PurchaseLedgerGstUpdateWorker,
)
from sams_accounting_desktop.workers.purchase_invoice_update_worker import PurchaseInvoiceSameAsExcelWorker
from sams_accounting_desktop.workers.purchase_reco_worker import PurchaseRecoWorker


class PurchaseRecoPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("workspace")
        self.selected_files: list[str] = []
        self.worker: PurchaseRecoWorker | None = None
        self.ledger_scan_worker: PurchaseLedgerGstScanWorker | None = None
        self.ledger_update_worker: PurchaseLedgerGstUpdateWorker | None = None
        self.invoice_update_worker: PurchaseInvoiceSameAsExcelWorker | None = None
        self.current_run: PurchaseRecoRun | None = None
        self.current_filter = "all"
        self.current_results: list[dict] = []
        self.visible_results: list[dict] = []
        self.filter_buttons: dict[str, AppButton] = {}
        self.ledger_gst_suggestions = []
        self.ledger_scan_manual = False
        self.pending_ledger_rescan = False
        self.ledger_scan_source_files: tuple[str, ...] | None = None
        self.active_ledger_scan_files: tuple[str, ...] = ()
        self.pending_reco_request: tuple[Decimal, Decimal] | None = None
        self.pending_reco_after_update: tuple[Decimal, Decimal] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(14)

        layout.addWidget(self.header())
        self.stepper = WorkflowStepper(["Ledger GST", "Upload GST", "Fetch Tally", "Review", "Export"])
        layout.addWidget(self.stepper)
        layout.addLayout(self.summary_cards())
        layout.addWidget(self.controls())
        layout.addWidget(self.results_panel())

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Purchase Reconciliation")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Compare GST purchase files with vouchers recorded in Tally.")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack)
        layout.addStretch()

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("connectorStatusIdle")
        layout.addWidget(self.status_label)
        return header

    def summary_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        self.gst_card = KpiCard("GST rows", "0", "Loaded from Excel", "#0f766e")
        self.tally_card = KpiCard("Tally purchases", "0", "Fetched from localhost", "#0f766e")
        self.matched_card = KpiCard("Matched", "0", "Exact matches", "#0f766e")
        self.review_card = KpiCard("Review", "0", "Probable or mismatch", "#0f766e")
        row.addWidget(self.gst_card)
        row.addWidget(self.tally_card)
        row.addWidget(self.matched_card)
        row.addWidget(self.review_card)
        return row

    def controls(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("recoPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        tally_label = QLabel("Tally URL")
        tally_label.setObjectName("mutedLabel")
        self.tally_url_input = QLineEdit(DEFAULT_TALLY_URL)
        self.tally_url_input.setObjectName("searchBox")
        form.addWidget(tally_label, 0, 0)
        form.addWidget(self.tally_url_input, 1, 0)

        amount_label = QLabel("Amount tolerance")
        amount_label.setObjectName("mutedLabel")
        self.amount_tolerance_input = QLineEdit("1.00")
        self.amount_tolerance_input.setObjectName("searchBox")
        form.addWidget(amount_label, 0, 1)
        form.addWidget(self.amount_tolerance_input, 1, 1)

        tax_label = QLabel("Tax tolerance")
        tax_label.setObjectName("mutedLabel")
        self.tax_tolerance_input = QLineEdit("1.00")
        self.tax_tolerance_input.setObjectName("searchBox")
        form.addWidget(tax_label, 0, 2)
        form.addWidget(self.tax_tolerance_input, 1, 2)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.select_button = AppButton("Select GST Excel", "secondary", "XL", "#2563eb")
        self.select_button.clicked.connect(self.select_files)
        self.clear_button = AppButton("Clear", "secondary", "CL", "#475467")
        self.clear_button.clicked.connect(self.clear_files)
        self.run_button = AppButton("Run Reconciliation", "primary", "GO", "#0f766e")
        self.run_button.clicked.connect(self.run_reco)
        self.export_excel_button = AppButton("Export Excel", "secondary", "EX", "#15803d")
        self.export_excel_button.clicked.connect(self.export_excel)
        self.export_pdf_button = AppButton("Export PDF", "secondary", "PF", "#b54708")
        self.export_pdf_button.clicked.connect(self.export_pdf)
        self.export_missing_button = AppButton("Export Missing", "secondary", "MS", "#b42318")
        self.export_missing_menu = QMenu(self.export_missing_button)
        self.export_missing_menu.addAction("Excel", self.export_missing_excel)
        self.export_missing_menu.addAction("PDF", self.export_missing_pdf)
        self.export_missing_button.setMenu(self.export_missing_menu)
        button_row.addWidget(self.select_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.run_button)
        button_row.addStretch()
        button_row.addWidget(self.export_missing_button)
        button_row.addWidget(self.export_excel_button)
        button_row.addWidget(self.export_pdf_button)
        layout.addLayout(button_row)

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(80)
        layout.addWidget(self.file_list)

        self.notice_label = QLabel("Select GST purchase Excel files to begin.")
        self.notice_label.setObjectName("toastInfo")
        self.notice_label.setWordWrap(True)
        layout.addWidget(self.notice_label)

        self.progress = QProgressBar()
        self.progress.setObjectName("healthProgress")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.set_export_enabled(False)
        return panel

    def results_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("recoPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Reconciliation Results")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self.same_as_excel_button = AppButton("Same as Excel", "primary", "EX", "#0f766e")
        self.same_as_excel_button.setEnabled(False)
        self.same_as_excel_button.clicked.connect(self.update_selected_invoice_same_as_excel)
        header.addWidget(self.same_as_excel_button)
        for label, status in [
            ("All", "all"),
            ("Matched", "matched"),
            ("Probable", "probable"),
            ("Mismatch", "mismatch"),
            ("Missing", "missing"),
        ]:
            button = AppButton(label, "secondary")
            button.clicked.connect(lambda _checked=False, value=status: self.set_filter(value))
            self.filter_buttons[status] = button
            header.addWidget(button)
        layout.addLayout(header)
        self.update_filter_buttons()

        self.results_table = QTableWidget(0, 14)
        self.results_table.setObjectName("resultTable")
        self.results_table.setHorizontalHeaderLabels(
            [
                "Select",
                "Status",
                "Probable %",
                "Party / Ledger",
                "Excel invoice",
                "Tally supplier invoice",
                "Suffix clue",
                "Excel amount",
                "Tally amount",
                "Diff",
                "Excel date",
                "Tally date",
                "Action",
                "Reason",
            ]
        )
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(False)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.setFocusPolicy(Qt.NoFocus)
        self.results_table.cellClicked.connect(self.handle_result_clicked)
        for column in range(13):
            self.results_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(13, QHeaderView.ResizeMode.Stretch)
        self.results_table.setMinimumHeight(360)

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self.results_table, 3)
        body.addWidget(self.detail_panel(), 1)
        layout.addLayout(body)
        return panel

    def detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("detailPanel")
        panel.setMinimumWidth(300)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Match Detail")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        self.detail_status = StatusChip("No selection", "info")
        layout.addWidget(self.detail_status)

        self.detail_supplier = QLabel("-")
        self.detail_supplier.setObjectName("detailValue")
        self.detail_supplier.setWordWrap(True)
        layout.addWidget(self.detail_supplier)

        self.detail_invoice = QLabel("-")
        self.detail_invoice.setObjectName("detailValue")
        self.detail_invoice.setWordWrap(True)
        layout.addWidget(self.detail_invoice)

        self.detail_amount = QLabel("-")
        self.detail_amount.setObjectName("detailValue")
        self.detail_amount.setWordWrap(True)
        layout.addWidget(self.detail_amount)

        self.detail_score = QLabel("-")
        self.detail_score.setObjectName("detailValue")
        self.detail_score.setWordWrap(True)
        layout.addWidget(self.detail_score)

        reasons_title = QLabel("Reasons")
        reasons_title.setObjectName("mutedLabel")
        layout.addWidget(reasons_title)

        self.detail_reasons = QLabel("Select any row to inspect the match.")
        self.detail_reasons.setObjectName("smallText")
        self.detail_reasons.setWordWrap(True)
        layout.addWidget(self.detail_reasons)
        layout.addStretch()
        return panel

    def select_files(self):
        files, _filter = QFileDialog.getOpenFileNames(
            self,
            "Select GST Purchase Excel",
            "",
            "Excel files (*.xlsx *.xlsm)",
        )
        if not files:
            return
        self.selected_files = files
        self.file_list.clear()
        self.file_list.addItems([Path(path).name for path in files])
        self.stepper.set_active(1)
        self.set_notice(f"{len(files)} GST Excel file selected. Ready to fetch Tally purchases.")
        self.scan_missing_gst_ledgers()

    def clear_files(self):
        self.selected_files = []
        self.file_list.clear()
        self.current_run = None
        self.current_results = []
        self.visible_results = []
        self.current_filter = "all"
        self.update_filter_buttons()
        self.results_table.setRowCount(0)
        self.update_detail(None)
        self.update_summary({})
        self.set_export_enabled(False)
        self.set_invoice_update_enabled(False)
        self.set_status("Ready", "connectorStatusIdle")
        self.stepper.set_active(0)
        self.set_notice("Select GST purchase Excel files to begin.")
        self.ledger_gst_suggestions = []
        self.ledger_scan_source_files = None

    def scan_missing_gst_ledgers(self, manual: bool = False):
        if self.ledger_scan_worker and self.ledger_scan_worker.isRunning():
            self.pending_ledger_rescan = self.active_ledger_scan_files != tuple(self.selected_files)
            return
        tally_url = self.tally_url_input.text().strip() or DEFAULT_TALLY_URL
        self.active_ledger_scan_files = tuple(self.selected_files)
        self.ledger_scan_manual = manual
        self.set_ledger_gst_busy(True, "Scanning Tally debtors/creditors without GSTIN...")
        self.ledger_scan_worker = PurchaseLedgerGstScanWorker(
            self.selected_files,
            tally_url=tally_url,
        )
        self.ledger_scan_worker.finished.connect(self.handle_ledger_scan_finished)
        self.ledger_scan_worker.finished.connect(self.ledger_scan_worker.deleteLater)
        self.ledger_scan_worker.start()

    def handle_ledger_scan_finished(self, ok: bool, message: str, payload: object):
        self.set_ledger_gst_busy(False)
        self.ledger_scan_worker = None
        should_rescan = self.pending_ledger_rescan
        self.pending_ledger_rescan = False
        if not ok:
            self.ledger_gst_suggestions = []
            if self.ledger_scan_manual:
                QMessageBox.warning(self, "Purchase Reconciliation", message)
            if should_rescan:
                QTimer.singleShot(50, self.scan_missing_gst_ledgers)
                return
            pending_request = self.pending_reco_request
            self.pending_reco_request = None
            if pending_request is not None:
                answer = QMessageBox.question(
                    self,
                    "GST Ledger Review Failed",
                    f"{message}\n\nGSTIN update skip karke reconciliation continue karna hai?",
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self.start_reco_worker(*pending_request)
                else:
                    self.set_notice("Reconciliation cancelled before Tally fetch.")
            return

        suggestions = list(payload or [])
        self.ledger_scan_source_files = self.active_ledger_scan_files
        self.populate_missing_gst_ledgers(suggestions)
        if should_rescan:
            QTimer.singleShot(50, self.scan_missing_gst_ledgers)
            return
        pending_request = self.pending_reco_request
        self.pending_reco_request = None
        if pending_request is not None:
            QTimer.singleShot(0, lambda request=pending_request: self.show_gst_review_popup_then_run(*request))

    def populate_missing_gst_ledgers(self, suggestions: list):
        self.ledger_gst_suggestions = suggestions

    def start_ledger_gst_update(self, selected_suggestions: list):
        self.set_ledger_gst_busy(True, "Updating selected ledger GSTINs in Tally...")
        self.ledger_update_worker = PurchaseLedgerGstUpdateWorker(
            selected_suggestions,
            tally_url=self.tally_url_input.text().strip() or DEFAULT_TALLY_URL,
        )
        self.ledger_update_worker.progress.connect(self.handle_ledger_update_progress)
        self.ledger_update_worker.finished.connect(self.handle_ledger_update_finished)
        self.ledger_update_worker.finished.connect(self.ledger_update_worker.deleteLater)
        self.ledger_update_worker.start()

    def handle_ledger_update_progress(self, current: int, total: int):
        self.set_notice(f"Tally ledger GSTIN update: {current}/{total}")

    def handle_ledger_update_finished(self, ok: bool, message: str, payload: object):
        self.set_ledger_gst_busy(False)
        self.ledger_update_worker = None
        pending_reco = self.pending_reco_after_update
        self.pending_reco_after_update = None
        results = list(payload or [])
        failed = [result for result in results if not getattr(result, "success", False)]
        if failed:
            failed_names = ", ".join(getattr(result, "ledger_name", "") for result in failed[:5])
            failed_message = f"{message} Failed: {failed_names}"
            self.set_notice(failed_message)
            QMessageBox.warning(self, "Purchase Reconciliation", failed_message)
            if pending_reco is not None:
                answer = QMessageBox.question(
                    self,
                    "Continue Reconciliation",
                    "Kuch ledger GSTIN update fail hue. Reconciliation fir bhi continue karna hai?",
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self.start_reco_worker(*pending_reco)
                else:
                    self.set_notice("Reconciliation cancelled after GSTIN update failure.")
            return
        self.set_notice(message + " Unregistered rows me koi change nahi kiya gaya.")
        if ok and pending_reco is None:
            QTimer.singleShot(500, self.scan_missing_gst_ledgers)
        if pending_reco is not None:
            self.start_reco_worker(*pending_reco)

    def run_reco(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Purchase Reconciliation", "GST purchase Excel file select karein.")
            return

        try:
            amount_tolerance = self.decimal_input(self.amount_tolerance_input.text())
            tax_tolerance = self.decimal_input(self.tax_tolerance_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Purchase Reconciliation", str(exc))
            return

        self.pending_reco_request = (amount_tolerance, tax_tolerance)
        self.set_notice("Pehle missing GST ledger popup review karein. User response ke baad reconciliation start hoga.")
        if self.ledger_scan_worker and self.ledger_scan_worker.isRunning():
            self.pending_ledger_rescan = self.active_ledger_scan_files != tuple(self.selected_files)
            return
        if self.ledger_scan_source_files != tuple(self.selected_files):
            self.scan_missing_gst_ledgers(manual=True)
            return
        self.pending_reco_request = None
        self.show_gst_review_popup_then_run(amount_tolerance, tax_tolerance)

    def show_gst_review_popup_then_run(self, amount_tolerance: Decimal, tax_tolerance: Decimal):
        dialog = LedgerGstReviewDialog(self.ledger_gst_suggestions, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.set_notice("Reconciliation cancelled before Tally fetch.")
            return

        if dialog.action == LedgerGstReviewDialog.ACTION_UPDATE:
            selected_suggestions = dialog.checked_suggestions()
            if not selected_suggestions:
                QMessageBox.warning(self, "Purchase Reconciliation", "Update ke liye koi suggested GSTIN checked nahi hai.")
                self.set_notice("Reconciliation cancelled before Tally fetch.")
                return
            self.pending_reco_after_update = (amount_tolerance, tax_tolerance)
            self.start_ledger_gst_update(selected_suggestions)
            return

        if dialog.action == LedgerGstReviewDialog.ACTION_CONTINUE:
            self.start_reco_worker(amount_tolerance, tax_tolerance)

    def start_reco_worker(self, amount_tolerance: Decimal, tax_tolerance: Decimal):
        self.set_busy(True)
        self.set_status("Working...", "connectorStatusIdle")
        self.stepper.set_active(3)
        self.set_notice("Fetching Tally purchases and preparing reconciliation.")
        self.results_table.setRowCount(0)
        self.set_invoice_update_enabled(False)
        self.worker = PurchaseRecoWorker(
            self.selected_files,
            tally_url=self.tally_url_input.text().strip() or DEFAULT_TALLY_URL,
            amount_tolerance=amount_tolerance,
            tax_tolerance=tax_tolerance,
        )
        self.worker.progress.connect(self.handle_progress)
        self.worker.finished.connect(self.handle_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def handle_progress(self, current: int, total: int):
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)

    def handle_finished(self, ok: bool, message: str, payload: object):
        self.set_busy(False)
        self.set_status("Completed" if ok else "Failed", "connectorStatusOk" if ok else "connectorStatusError")
        if not ok or not isinstance(payload, PurchaseRecoRun):
            self.stepper.set_active(1 if self.selected_files else 0)
            self.set_notice(message)
            QMessageBox.warning(self, "Purchase Reconciliation", message)
            return

        self.current_run = payload
        self.update_summary(payload.summary)
        self.populate_results(payload.results)
        self.set_export_enabled(True)
        self.set_invoice_update_enabled(self.has_same_as_excel_candidates())
        self.stepper.set_active(4)
        self.set_notice(message + " Review results or export the report.")

    def update_summary(self, summary: dict):
        self.update_card(self.gst_card, str(summary.get("gst_count", 0)))
        self.update_card(self.tally_card, str(summary.get("tally_count", 0)))
        self.update_card(self.matched_card, str(summary.get("matched_count", 0)))
        review_count = (
            summary.get("probable_count", 0)
            + summary.get("mismatch_count", 0)
            + summary.get("missing_count", 0)
        )
        self.update_card(self.review_card, str(review_count))

    def set_filter(self, status: str):
        self.current_filter = status
        self.update_filter_buttons()
        self.populate_results()

    def update_filter_buttons(self):
        for status, button in self.filter_buttons.items():
            button.setObjectName("filterActive" if status == self.current_filter else "filterButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def filtered_results(self) -> list[dict]:
        if self.current_filter == "all":
            results = list(self.current_results)
        else:
            results = [result for result in self.current_results if result.get("status") == self.current_filter]
        return sorted(results, key=self.match_sort_key, reverse=True)

    def populate_results(self, results: list[dict] | None = None):
        if results is not None:
            self.current_results = list(results)
        self.visible_results = self.filtered_results()
        self.results_table.setRowCount(len(self.visible_results))
        self.update_detail(None)
        for row_index, result in enumerate(self.visible_results):
            gst = result.get("gst")
            tally = result.get("tally")
            status = result.get("status", "")
            if self.is_same_as_excel_candidate(result):
                self.results_table.setCellWidget(row_index, 0, self.check_widget(False, enabled=True))
            else:
                check_item = QTableWidgetItem("")
                check_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                self.results_table.setItem(row_index, 0, check_item)

            values = [
                status,
                self.probable_percent_text(result),
                self.party_compare_text(gst, tally),
                getattr(gst, "invoice_number", "") if gst is not None else "",
                getattr(tally, "supplier_invoice_number", "") if tally is not None else "",
                self.invoice_suffix_clue(gst, tally),
                self.format_amount(getattr(gst, "invoice_value", None) if gst is not None else None),
                self.format_amount(getattr(tally, "amount", None) if tally is not None else None),
                self.amount_diff_text(gst, tally),
                self.format_date(getattr(gst, "invoice_date", None) if gst is not None else None),
                self.format_date(getattr(tally, "date", None) if tally is not None else None),
                self.action_text(result),
                self.reason_text(result),
            ]
            for column, value in enumerate(values):
                table_column = column + 1
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 0:
                    item.setForeground(self.status_color(value))
                elif table_column == 2:
                    item.setForeground(self.probable_percent_color(result))
                elif table_column in {6, 9, 12} and status == "probable":
                    item.setForeground(QColor("#b54708"))
                elif table_column == 9 and value not in {"", "0.00"}:
                    item.setForeground(QColor("#b42318"))
                self.results_table.setItem(row_index, table_column, item)

        if self.visible_results:
            self.results_table.selectRow(0)
            self.update_detail(self.visible_results[0])

    def handle_result_clicked(self, row: int, _column: int):
        if 0 <= row < len(self.visible_results):
            self.update_detail(self.visible_results[row])

    def update_detail(self, result: dict | None):
        if result is None:
            self.detail_status.set_status("info", "No selection")
            self.detail_supplier.setText("-")
            self.detail_invoice.setText("-")
            self.detail_amount.setText("-")
            self.detail_score.setText("-")
            self.detail_reasons.setText("Select any row to inspect the match.")
            return

        gst = result.get("gst")
        tally = result.get("tally")
        status = result.get("status", "")
        chip_status = {
            "matched": "ok",
            "probable": "warning",
            "mismatch": "error",
            "missing": "error",
        }.get(status, "info")
        self.detail_status.set_status(chip_status, status.title() if status else "Review")
        self.detail_supplier.setText(
            f"Supplier: {getattr(gst, 'supplier_name', '') or '-'}\nGSTIN: {getattr(gst, 'supplier_gstin', '') or '-'}"
            if gst is not None
            else "Supplier: -"
        )
        self.detail_invoice.setText(
            "Excel invoice: "
            + (getattr(gst, "invoice_number", "") if gst is not None else "-")
            + "\nTally supplier invoice: "
            + (getattr(tally, "supplier_invoice_number", "") if tally is not None else "-")
            + "\nTally voucher: "
            + (getattr(tally, "voucher_number", "") if tally is not None else "-")
        )
        self.detail_amount.setText(
            "GST amount: "
            + self.format_amount(getattr(gst, "invoice_value", None) if gst is not None else None)
            + "\nTally amount: "
            + self.format_amount(getattr(tally, "amount", None) if tally is not None else None)
        )
        self.detail_score.setText(self.confidence_detail_text(result))
        self.detail_reasons.setText("\n".join(result.get("reasons", []) or ["No reasons available"]))

    def party_compare_text(self, gst, tally) -> str:
        gst_party = getattr(gst, "supplier_name", "") if gst is not None else ""
        tally_party = getattr(tally, "party_ledger_name", "") if tally is not None else ""
        if gst_party and tally_party and gst_party.strip().casefold() != tally_party.strip().casefold():
            return f"{gst_party} / {tally_party}"
        return gst_party or tally_party or ""

    def invoice_suffix_clue(self, gst, tally) -> str:
        if gst is None or tally is None:
            return ""
        excel_invoice = getattr(gst, "invoice_number", "") or ""
        tally_invoice = getattr(tally, "supplier_invoice_number", "") or ""
        if not excel_invoice or not tally_invoice:
            return "Tally supplier invoice blank" if excel_invoice else ""
        if self.invoice_text_key(excel_invoice) == self.invoice_text_key(tally_invoice):
            return "Full invoice match"

        common_suffixes = invoice_digit_suffixes(excel_invoice) & invoice_digit_suffixes(tally_invoice)
        if common_suffixes:
            suffix = max(common_suffixes, key=lambda value: (len(value), value))
            return f"Last {len(suffix)} digits match: {suffix}"
        return "Supplier invoice mismatch"

    def amount_diff_text(self, gst, tally) -> str:
        if gst is None or tally is None:
            return ""
        gst_amount = Decimal(getattr(gst, "invoice_value", None) or 0).quantize(Decimal("0.01"))
        tally_amount = Decimal(getattr(tally, "amount", None) or 0).quantize(Decimal("0.01"))
        diff = (gst_amount - tally_amount).copy_abs().quantize(Decimal("0.01"))
        return f"{diff:.2f}"

    def match_sort_key(self, result: dict) -> tuple[int, int, int]:
        status_rank = {
            "matched": 4,
            "probable": 3,
            "mismatch": 2,
            "missing": 1,
        }.get(result.get("status", ""), 0)
        if result.get("status") == "probable":
            return (status_rank, self.probable_confidence(result), self.raw_match_score(result))
        return (status_rank, 0, self.raw_match_score(result))

    def probable_percent_text(self, result: dict) -> str:
        if result.get("status") != "probable":
            return ""
        return f"{self.probable_confidence(result)}%"

    def probable_confidence(self, result: dict) -> int:
        if result.get("status") != "probable":
            return 0

        gst = result.get("gst")
        tally = result.get("tally")
        confidence = 0

        suffix_length = self.invoice_suffix_length(gst, tally)
        if suffix_length >= 5:
            confidence += 40
        elif suffix_length == 4:
            confidence += 34
        elif suffix_length == 3:
            confidence += 27
        elif suffix_length == 2:
            confidence += 18

        amount_diff = self.amount_diff_value(gst, tally)
        if amount_diff is not None:
            if amount_diff <= Decimal("0.01"):
                confidence += 25
            elif amount_diff <= Decimal("1.00"):
                confidence += 22
            elif amount_diff <= Decimal("5.00"):
                confidence += 14
            elif amount_diff <= Decimal("25.00"):
                confidence += 7

        day_difference = self.date_difference(gst, tally)
        if day_difference is None:
            confidence += 4
        elif day_difference == 0:
            confidence += 15
        elif day_difference <= 3:
            confidence += 10
        else:
            confidence -= min(15, day_difference)

        reason_text = " ".join(result.get("reasons", []) or []).casefold()
        if "gstin matched" in reason_text:
            confidence += 15
        elif "supplier name similar" in reason_text:
            confidence += 12
        elif "supplier name partially matched" in reason_text:
            confidence += 7
        if "taxable value matched" in reason_text:
            confidence += 5
        if "gstin mismatch" in reason_text:
            confidence -= 20
        if "invoice suffix ignored" in reason_text:
            confidence -= 15

        return max(1, min(98, confidence))

    def confidence_detail_text(self, result: dict) -> str:
        status = result.get("status", "")
        if status == "probable":
            return f"Probable confidence: {self.probable_confidence(result)}%"
        if status == "matched":
            return "Exact match"
        if status == "missing":
            return "No reliable match"
        return "Review required"

    def invoice_suffix_length(self, gst, tally) -> int:
        if gst is None or tally is None:
            return 0
        excel_invoice = getattr(gst, "invoice_number", "") or ""
        tally_invoice = getattr(tally, "supplier_invoice_number", "") or ""
        common_suffixes = invoice_digit_suffixes(excel_invoice) & invoice_digit_suffixes(tally_invoice)
        return max((len(suffix) for suffix in common_suffixes), default=0)

    def amount_diff_value(self, gst, tally) -> Decimal | None:
        if gst is None or tally is None:
            return None
        gst_amount = Decimal(getattr(gst, "invoice_value", None) or 0).quantize(Decimal("0.01"))
        tally_amount = Decimal(getattr(tally, "amount", None) or 0).quantize(Decimal("0.01"))
        return (gst_amount - tally_amount).copy_abs().quantize(Decimal("0.01"))

    @staticmethod
    def date_difference(gst, tally) -> int | None:
        if gst is None or tally is None:
            return None
        gst_date = getattr(gst, "invoice_date", None)
        tally_date = getattr(tally, "date", None)
        if not gst_date or not tally_date:
            return None
        return abs((gst_date - tally_date).days)

    @staticmethod
    def raw_match_score(result: dict) -> int:
        try:
            return int(round(float(result.get("score", 0) or 0)))
        except (TypeError, ValueError):
            return 0

    def probable_percent_color(self, result: dict) -> QColor:
        if result.get("status") != "probable":
            return QColor("#101828")
        percent = self.probable_confidence(result)
        if percent >= 80:
            return QColor("#067647")
        if percent >= 50:
            return QColor("#b54708")
        return QColor("#b42318")

    def action_text(self, result: dict) -> str:
        if result.get("invoice_updated"):
            return "Updated same as Excel"
        status = result.get("status", "")
        if status == "probable":
            return "Review suffix, then accept manually"
        if status == "matched":
            return "OK"
        if status == "mismatch":
            return "Check amount/date/tax"
        if status == "missing":
            return "Tally supplier invoice not found"
        return "Review"

    def reason_text(self, result: dict) -> str:
        if result.get("invoice_updated"):
            return result.get("invoice_update_message", "") or "Tally supplier invoice updated same as Excel"
        gst = result.get("gst")
        tally = result.get("tally")
        status = result.get("status", "")
        if status == "probable":
            clue = self.invoice_suffix_clue(gst, tally)
            checks = []
            if self.amount_diff_text(gst, tally) == "0.00":
                checks.append("amount same")
            else:
                checks.append("amount diff")
            gst_date = getattr(gst, "invoice_date", None) if gst is not None else None
            tally_date = getattr(tally, "date", None) if tally is not None else None
            if gst_date and tally_date:
                checks.append("date same" if gst_date == tally_date else f"date diff {abs((gst_date - tally_date).days)} days")
            return f"{clue}; {', '.join(checks)}"
        return ", ".join(result.get("reasons", []) or [])

    def is_same_as_excel_candidate(self, result: dict) -> bool:
        gst = result.get("gst")
        tally = result.get("tally")
        excel_invoice = getattr(gst, "invoice_number", "") if gst is not None else ""
        return bool(gst is not None and tally is not None and excel_invoice and getattr(tally, "raw_xml", ""))

    def has_same_as_excel_candidates(self) -> bool:
        return any(self.is_same_as_excel_candidate(result) for result in self.current_results)

    def selected_same_as_excel_results(self) -> list[dict]:
        selected: list[dict] = []
        for row_index, result in enumerate(self.visible_results):
            checkbox = self.checkbox_at(self.results_table, row_index)
            if checkbox and checkbox.isChecked() and self.is_same_as_excel_candidate(result):
                selected.append(result)

        if selected:
            return selected

        current_row = self.results_table.currentRow()
        if 0 <= current_row < len(self.visible_results):
            result = self.visible_results[current_row]
            if self.is_same_as_excel_candidate(result):
                return [result]
        return []

    def update_selected_invoice_same_as_excel(self):
        if self.invoice_update_worker and self.invoice_update_worker.isRunning():
            return

        selected_results = self.selected_same_as_excel_results()
        if not selected_results:
            QMessageBox.warning(
                self,
                "Purchase Reconciliation",
                "Same as Excel ke liye pehle valid Tally matched/probable row select karein.",
            )
            return

        dialog = SameAsExcelReviewDialog(selected_results, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected_results = dialog.checked_results()
        if not selected_results:
            QMessageBox.warning(
                self,
                "Same as Excel",
                "Update ke liye koi entry selected nahi hai.",
            )
            return

        self.set_busy(True)
        self.set_status("Updating...", "connectorStatusIdle")
        self.set_notice("Selected Tally purchase bill number same as Excel update ho rahe hain.")
        self.invoice_update_worker = PurchaseInvoiceSameAsExcelWorker(
            selected_results,
            tally_url=self.tally_url_input.text().strip() or DEFAULT_TALLY_URL,
        )
        self.invoice_update_worker.progress.connect(self.handle_invoice_update_progress)
        self.invoice_update_worker.completed.connect(self.handle_invoice_update_finished)
        self.invoice_update_worker.finished.connect(self.handle_invoice_update_thread_finished)
        self.invoice_update_worker.finished.connect(self.invoice_update_worker.deleteLater)
        self.invoice_update_worker.start()

    def handle_invoice_update_progress(self, current: int, total: int):
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)
        self.set_notice(f"Same as Excel update: {current}/{total}")

    def handle_invoice_update_finished(self, ok: bool, message: str, payload: object):
        self.set_busy(False)
        update_results = list(payload or [])
        failed = [result for result in update_results if not getattr(result, "success", False)]

        self.populate_results()
        self.set_invoice_update_enabled(self.has_same_as_excel_candidates())
        self.set_status("Updated" if ok else "Review", "connectorStatusOk" if ok else "connectorStatusError")
        self.set_notice(message + " Table refreshed.")

        if failed:
            failed_rows = ", ".join(
                (
                    getattr(result, "voucher_number", "")
                    or getattr(result, "party_ledger_name", "")
                    or getattr(result, "new_invoice_number", "")
                    or "row"
                )
                for result in failed[:5]
            )
            QMessageBox.warning(
                self,
                "Same as Excel",
                f"Kuch voucher update nahi hue: {failed_rows}",
            )

    def handle_invoice_update_thread_finished(self):
        self.invoice_update_worker = None

    def export_excel(self):
        if self.current_run is None:
            return
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Purchase Reconciliation Excel",
            "purchase-reconciliation-result.xlsx",
            "Excel files (*.xlsx)",
        )
        if file_path:
            export_purchase_reco_excel(self.current_run, file_path)
            self.set_status("Excel exported", "connectorStatusOk")
            self.set_notice(f"Excel report exported: {Path(file_path).name}")

    def export_pdf(self):
        if self.current_run is None:
            return
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Purchase Reconciliation PDF",
            "purchase-reconciliation-result.pdf",
            "PDF files (*.pdf)",
        )
        if file_path:
            export_purchase_reco_pdf(self.current_run, file_path)
            self.set_status("PDF exported", "connectorStatusOk")
            self.set_notice(f"PDF report exported: {Path(file_path).name}")

    def missing_results(self) -> list[dict]:
        return [result for result in self.current_results if result.get("status") == "missing"]

    def export_missing_excel(self):
        missing_results = self.missing_results()
        if not missing_results:
            QMessageBox.information(self, "Purchase Reconciliation", "Missing entries export ke liye available nahi hain.")
            return
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Missing Purchase Reconciliation Excel",
            "purchase-reconciliation-missing.xlsx",
            "Excel files (*.xlsx)",
        )
        if file_path:
            export_reconciliation_to_excel(missing_results, file_path)
            self.set_status("Missing Excel exported", "connectorStatusOk")
            self.set_notice(f"Missing Excel report exported: {Path(file_path).name}")

    def export_missing_pdf(self):
        missing_results = self.missing_results()
        if not missing_results:
            QMessageBox.information(self, "Purchase Reconciliation", "Missing entries export ke liye available nahi hain.")
            return
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Missing Purchase Reconciliation PDF",
            "purchase-reconciliation-missing.pdf",
            "PDF files (*.pdf)",
        )
        if file_path:
            export_reconciliation_to_pdf(missing_results, file_path)
            self.set_status("Missing PDF exported", "connectorStatusOk")
            self.set_notice(f"Missing PDF report exported: {Path(file_path).name}")

    def set_busy(self, busy: bool):
        self.select_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.set_export_enabled(bool(self.current_run) and not busy)
        self.set_invoice_update_enabled(self.has_same_as_excel_candidates() and not busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1 if self.current_run else 0)

    def set_ledger_gst_busy(self, _busy: bool, _message: str = ""):
        return

    def set_export_enabled(self, enabled: bool):
        self.export_excel_button.setEnabled(enabled)
        self.export_pdf_button.setEnabled(enabled)
        self.export_missing_button.setEnabled(enabled and bool(self.missing_results()))

    def set_invoice_update_enabled(self, enabled: bool):
        if hasattr(self, "same_as_excel_button"):
            self.same_as_excel_button.setEnabled(enabled)

    def set_status(self, text: str, object_name: str):
        self.status_label.setText(text)
        self.status_label.setObjectName(object_name)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_notice(self, text: str):
        self.notice_label.setText(text)

    @staticmethod
    def update_card(card: KpiCard, value: str):
        label = card.findChild(QLabel, "kpiValue")
        if label is not None:
            label.setText(value)

    @staticmethod
    def decimal_input(value: str) -> Decimal:
        try:
            return Decimal(value.strip() or "0.00")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Tolerance numeric value hona chahiye.") from exc

    @staticmethod
    def format_date(value) -> str:
        return value.isoformat() if value else ""

    @staticmethod
    def format_amount(value) -> str:
        return f"{Decimal(value or 0):.2f}"

    @staticmethod
    def invoice_text_key(value: str) -> str:
        digits = only_digits(value)
        if digits and str(value or "").strip().isdigit():
            return digits
        return "".join(str(value or "").casefold().split())

    @staticmethod
    def status_color(status: str) -> QColor:
        return {
            "matched": QColor("#067647"),
            "probable": QColor("#b54708"),
            "mismatch": QColor("#b42318"),
            "missing": QColor("#b42318"),
        }.get(status, QColor("#101828"))

    @staticmethod
    def check_widget(checked: bool, *, enabled: bool = True) -> QCheckBox:
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setEnabled(enabled)
        checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return checkbox

    @staticmethod
    def checkbox_at(table: QTableWidget, row_index: int) -> QCheckBox | None:
        widget = table.cellWidget(row_index, 0)
        return widget if isinstance(widget, QCheckBox) else None


class SameAsExcelReviewDialog(QDialog):
    def __init__(self, results: list[dict], parent: PurchaseRecoPanel | None = None):
        super().__init__(parent)
        self.results = list(results)
        self.panel = parent

        self.setWindowTitle("Same as Excel Review")
        self.setMinimumSize(980, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Review selected entries")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        body = QLabel(
            f"{len(self.results)} selected purchase voucher ka supplier invoice number Excel invoice number se update hoga."
        )
        body.setObjectName("smallText")
        body.setWordWrap(True)
        layout.addWidget(body)

        self.table = QTableWidget(0, 8)
        self.table.setObjectName("resultTable")
        self.table.setHorizontalHeaderLabels(
            [
                "OK",
                "Status",
                "Party / Ledger",
                "Excel invoice",
                "Tally invoice",
                "Excel amount",
                "Tally amount",
                "Reason",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for column in range(3, 7):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.populate_table()

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = AppButton("Cancel", "secondary", "CL", "#475467")
        update_button = AppButton("Same as Excel", "primary", "EX", "#0f766e")
        cancel_button.clicked.connect(self.reject)
        update_button.clicked.connect(self.accept_update)
        button_row.addWidget(cancel_button)
        button_row.addWidget(update_button)
        layout.addLayout(button_row)

    def populate_table(self):
        self.table.setRowCount(len(self.results))
        for row_index, result in enumerate(self.results):
            gst = result.get("gst")
            tally = result.get("tally")
            self.table.setCellWidget(row_index, 0, PurchaseRecoPanel.check_widget(True, enabled=True))

            values = [
                result.get("status", ""),
                self.party_compare_text(gst, tally),
                getattr(gst, "invoice_number", "") if gst is not None else "",
                getattr(tally, "supplier_invoice_number", "") if tally is not None else "",
                self.format_amount(getattr(gst, "invoice_value", None) if gst is not None else None),
                self.format_amount(getattr(tally, "amount", None) if tally is not None else None),
                self.reason_text(result),
            ]
            for column, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 1:
                    item.setForeground(PurchaseRecoPanel.status_color(value))
                self.table.setItem(row_index, column, item)

        if self.results:
            self.table.selectRow(0)

    def checked_results(self) -> list[dict]:
        selected = []
        for row_index, result in enumerate(self.results):
            checkbox = PurchaseRecoPanel.checkbox_at(self.table, row_index)
            if checkbox and checkbox.isChecked():
                selected.append(result)
        return selected

    def accept_update(self):
        if not self.checked_results():
            QMessageBox.warning(self, "Same as Excel", "Update ke liye koi entry checked nahi hai.")
            return
        self.accept()

    def party_compare_text(self, gst, tally) -> str:
        if self.panel is not None:
            return self.panel.party_compare_text(gst, tally)
        gst_party = getattr(gst, "supplier_name", "") if gst is not None else ""
        tally_party = getattr(tally, "party_ledger_name", "") if tally is not None else ""
        return gst_party or tally_party or ""

    def reason_text(self, result: dict) -> str:
        if self.panel is not None:
            return self.panel.reason_text(result)
        return ", ".join(result.get("reasons", []) or [])

    @staticmethod
    def format_amount(value) -> str:
        return PurchaseRecoPanel.format_amount(value)


class LedgerGstReviewDialog(QDialog):
    ACTION_CANCEL = "cancel"
    ACTION_UPDATE = "update"
    ACTION_CONTINUE = "continue"

    def __init__(self, suggestions: list, parent: QWidget | None = None):
        super().__init__(parent)
        self.suggestions = list(suggestions)
        self.action = self.ACTION_CANCEL

        self.setWindowTitle("Missing GST Ledger Review")
        self.setMinimumSize(900, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Review missing GST ledgers")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        suggested_count = sum(1 for suggestion in self.suggestions if getattr(suggestion, "suggested_gstin", ""))
        unregistered_count = len(self.suggestions) - suggested_count
        body = QLabel(
            f"{len(self.suggestions)} debtors/creditors ledgers me GSTIN missing hai. "
            f"{suggested_count} rows me Excel se GSTIN suggested hai, "
            f"{unregistered_count} rows Unregistered rahenge."
        )
        body.setObjectName("smallText")
        body.setWordWrap(True)
        layout.addWidget(body)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("resultTable")
        self.table.setHorizontalHeaderLabels(["OK", "Ledger", "Group", "Excel Party", "GSTIN / Status", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(2, 6):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        self.populate_table()

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = AppButton("Cancel", "secondary", "CL", "#475467")
        continue_button = AppButton("Continue Without Update", "secondary", "SK", "#b54708")
        self.update_button = AppButton("Update Selected & Continue", "primary", "OK", "#15803d")
        self.update_button.setEnabled(suggested_count > 0)
        cancel_button.clicked.connect(self.reject)
        continue_button.clicked.connect(self.accept_continue)
        self.update_button.clicked.connect(self.accept_update)
        button_row.addWidget(cancel_button)
        button_row.addWidget(continue_button)
        button_row.addWidget(self.update_button)
        layout.addLayout(button_row)

    def populate_table(self):
        self.table.setRowCount(len(self.suggestions))
        for row_index, suggestion in enumerate(self.suggestions):
            check_item = QTableWidgetItem("")
            if getattr(suggestion, "suggested_gstin", ""):
                check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                check_item.setCheckState(Qt.CheckState.Checked)
            else:
                check_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                check_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row_index, 0, check_item)

            gstin_text = getattr(suggestion, "suggested_gstin", "") or "Unregistered"
            status = getattr(suggestion, "status", "")
            status_text = {
                "suggested": "Excel match suggested",
                "review": "Review manually",
                "unregistered": "Unregistered - no change",
            }.get(status, status.title() if status else "")
            values = [
                getattr(suggestion, "ledger_name", ""),
                getattr(suggestion, "parent", ""),
                getattr(suggestion, "suggested_party_name", ""),
                gstin_text,
                status_text,
            ]
            for column, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 4 and gstin_text == "Unregistered":
                    item.setForeground(QColor("#b54708"))
                elif column == 5 and status == "suggested":
                    item.setForeground(QColor("#067647"))
                self.table.setItem(row_index, column, item)

        if self.suggestions:
            self.table.selectRow(0)

    def checked_suggestions(self) -> list:
        selected = []
        for row_index, suggestion in enumerate(self.suggestions):
            if not getattr(suggestion, "suggested_gstin", ""):
                continue
            check_item = self.table.item(row_index, 0)
            if check_item and check_item.checkState() == Qt.CheckState.Checked:
                selected.append(suggestion)
        return selected

    def accept_update(self):
        if not self.checked_suggestions():
            QMessageBox.warning(self, "Purchase Reconciliation", "Update ke liye koi suggested GSTIN checked nahi hai.")
            return
        self.action = self.ACTION_UPDATE
        self.accept()

    def accept_continue(self):
        self.action = self.ACTION_CONTINUE
        self.accept()
