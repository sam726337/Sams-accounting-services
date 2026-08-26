from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import re
import time

from PySide6.QtCore import QDate, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.sales_generator import (
    build_fixed_sale_preview_entries,
    build_random_sale_preview_entries,
    extract_gst_rate_from_stock_item_name,
    parse_fixed_sale_excel_rows,
)
from sams_accounting_desktop.services.tally_client import (
    create_tally_item_invoice_voucher,
    fetch_tally_groups,
    fetch_tally_ledger_masters,
    fetch_tally_stock_item_masters,
    fetch_tally_voucher_types,
    filter_tally_ledger_names_by_groups,
)
from sams_accounting_desktop.ui.components import AppButton, StatusChip
from sams_accounting_desktop.ui.icons import make_icon


class RandomCalculationNotPossibleError(ValueError):
    pass


class SalesImportWorker(QThread):
    progress = Signal(int, int, int, int, float, float)
    completed = Signal(int, int, list, str)

    def __init__(self, tally_url: str, entries: list[dict]):
        super().__init__()
        self.tally_url = tally_url
        self.entries = list(entries)

    def run(self):
        created = 0
        failed = 0
        failed_entries: list[dict] = []
        first_error = ""
        total = len(self.entries)
        started_at = time.monotonic()
        self.progress.emit(0, total, created, failed, 0.0, -1.0)

        for current, entry in enumerate(self.entries, start=1):
            try:
                result = create_tally_item_invoice_voucher(
                    self.tally_url,
                    voucher_type=entry.get("voucher_type") or "Sales",
                    voucher_date=entry["voucher_date"],
                    party_ledger=entry.get("party_ledger") or entry.get("cash_bank_ledger", ""),
                    sales_ledger=entry["sale_ledger"],
                    stock_item_name=entry["stock_item_name"],
                    taxable_amount=Decimal(entry["taxable_amount"]),
                    total_amount=Decimal(entry["amount"]),
                    cgst_ledger=entry.get("cgst_ledger", ""),
                    sgst_ledger=entry.get("sgst_ledger", ""),
                    cgst_rate=Decimal(entry.get("cgst_rate", "0.00")),
                    sgst_rate=Decimal(entry.get("sgst_rate", "0.00")),
                    round_off_ledger=entry.get("round_off_ledger", ""),
                    round_off_amount=Decimal(entry.get("round_off_amount", "0.00")),
                    narration=entry["narration"],
                    voucher_number=str(entry.get("bill_number", "")),
                    item_rate=entry.get("item_rate"),
                    billed_quantity=entry.get("billed_quantity"),
                )
                if result.success:
                    created += 1
                else:
                    failed += 1
                    failed_entries.append(entry)
                    first_error = first_error or result.message
            except Exception as exc:
                failed += 1
                failed_entries.append(entry)
                first_error = first_error or str(exc)

            elapsed = time.monotonic() - started_at
            remaining = (elapsed / current) * (total - current) if current else -1.0
            self.progress.emit(current, total, created, failed, elapsed, remaining)

        self.completed.emit(created, failed, failed_entries, first_error)


class SalesChoicePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("workspace")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.choice_page = self.build_choice_page()
        self.random_sale_panel = RandomSalePanel(self.open_choices)
        self.fixed_sale_panel = FixedSalePanel(self.open_choices)

        self.stack.addWidget(self.choice_page)
        self.stack.addWidget(self.random_sale_panel)
        self.stack.addWidget(self.fixed_sale_panel)
        layout.addWidget(self.stack)

    def build_choice_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("workspace")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(self.header())

        choice_row = QHBoxLayout()
        choice_row.setSpacing(18)
        choice_row.addWidget(
            self.choice_card(
                "Random Sale",
                "Generate split taxable bills with GST, dates, round-off, preview, and Tally import.",
                "Ready",
                "#be123c",
                "RS",
                self.open_random_sale,
            )
        )
        choice_row.addWidget(
            self.choice_card(
                "Fixed Sale",
                "Excel based controlled sale flow.",
                "Next",
                "#0f766e",
                "FS",
                self.open_fixed_sale,
            )
        )
        layout.addLayout(choice_row)

        self.selection_status = StatusChip("Select sales mode", "info")
        layout.addWidget(self.selection_status)
        layout.addStretch()
        return page

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Sales Generator")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Choose sales creation mode")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack)
        layout.addStretch()
        layout.addWidget(StatusChip("Ready", "info"))
        return header

    def choice_card(
        self,
        title: str,
        subtitle: str,
        badge: str,
        accent: str,
        initials: str,
        handler,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("choiceCard")
        card.setMinimumHeight(260)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(make_icon(initials, accent, 54, 12).pixmap(54, 54))
        top.addWidget(icon)
        top.addStretch()
        chip = QLabel(badge)
        chip.setObjectName("badge")
        top.addWidget(chip)
        layout.addLayout(top)

        heading = QLabel(title)
        heading.setObjectName("choiceTitle")
        layout.addWidget(heading)

        body = QLabel(subtitle)
        body.setObjectName("choiceBody")
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        button = AppButton(f"Open {title}", "primary", initials, accent)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return card

    def open_choices(self):
        self.stack.setCurrentWidget(self.choice_page)

    def open_random_sale(self):
        self.selection_status.set_status("warning", "Random Sale selected")
        self.stack.setCurrentWidget(self.random_sale_panel)

    def open_fixed_sale(self):
        self.selection_status.set_status("ok", "Fixed Sale selected")
        self.stack.setCurrentWidget(self.fixed_sale_panel)


class RandomSalePanel(QWidget):
    REQUIRED_FIELDS = (
        "sale_ledger",
        "voucher_type",
        "stock_item_name",
    )

    def __init__(self, back_handler):
        super().__init__()
        self.setObjectName("workspace")
        self.back_handler = back_handler
        self.preview_entries: list[dict] = []
        self.master_value_lookups: dict[str, set[str]] = {}
        self.stock_item_gst_rates: dict[str, tuple[Decimal, Decimal, Decimal]] = {}
        self.import_worker: SalesImportWorker | None = None
        self.import_started_at = 0.0
        self.import_progress_current = 0
        self.import_progress_total = 0
        self.import_created = 0
        self.import_failed = 0
        self.import_timer = QTimer(self)
        self.import_timer.setInterval(500)
        self.import_timer.timeout.connect(self.refresh_import_timer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(self.header())

        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(self.form_panel(), 0)
        body.addWidget(self.preview_panel(), 1)
        layout.addLayout(body)

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Random Sale")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Same random sale logic: split taxable total, spread dates, calculate GST, preview, then import.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack, 1)
        self.status_chip = StatusChip("Ready", "info")
        layout.addWidget(self.status_chip)
        back_button = AppButton("Back", "secondary", "BA", "#475467")
        back_button.clicked.connect(self.back_handler)
        layout.addWidget(back_button)
        return header

    def form_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("formPanel")
        panel.setFixedWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Entry Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.from_date_input = self.date_edit(QDate.currentDate())
        self.to_date_input = self.date_edit(QDate.currentDate())
        self.sale_against_input = QComboBox()
        self.sale_against_input.setObjectName("masterCombo")
        self.sale_against_input.addItem("Cash / Bank Sale", "cash_bank")
        self.sale_against_input.addItem("Party Sale", "party")
        self.party_name_input = self.master_combo("ABC Traders", "Select party ledger from Tally")
        self.cash_bank_ledger_input = self.master_combo("Cash", "Select cash / bank ledger from Tally")
        self.sale_ledger_input = self.master_combo("Sales", "Select sales ledger from Tally")
        self.voucher_type_input = self.master_combo("Sales", "Select voucher type from Tally")
        self.stock_item_name_input = self.master_combo("18 % Item", "Select stock item from Tally")
        self.cgst_ledger_input = self.master_combo("Output CGST", "Optional CGST ledger")
        self.sgst_ledger_input = self.master_combo("Output SGST", "Optional SGST ledger")
        self.round_off_ledger_input = self.master_combo("Round Off", "Optional round-off ledger")
        self.stock_item_name_input.currentTextChanged.connect(self.suggest_gst_ledgers_for_stock_item)
        self.bill_count_input = QSpinBox()
        self.bill_count_input.setObjectName("numberInput")
        self.bill_count_input.setRange(1, 500)
        self.bill_count_input.setValue(10)
        self.min_amount_input = self.line_edit("100.00")
        self.max_amount_input = self.line_edit("10000.00")
        self.taxable_amount_input = self.line_edit("10000.00")
        self.narration_prefix_input = self.line_edit("")
        self.tally_url_input = self.line_edit(DEFAULT_TALLY_URL)

        fields = [
            ("From Date", self.from_date_input),
            ("To Date", self.to_date_input),
            ("Sale Against", self.sale_against_input),
            ("Party Name", self.party_name_input),
            ("Cash / Bank Ledger", self.cash_bank_ledger_input),
            ("Sales Ledger", self.sale_ledger_input),
            ("Voucher Type", self.voucher_type_input),
            ("Stock Item Name", self.stock_item_name_input),
            ("CGST Ledger", self.cgst_ledger_input),
            ("SGST Ledger", self.sgst_ledger_input),
            ("Round Off Ledger", self.round_off_ledger_input),
            ("Number of Bills", self.bill_count_input),
            ("Minimum Amount", self.min_amount_input),
            ("Maximum Amount", self.max_amount_input),
            ("Total Taxable Amount", self.taxable_amount_input),
            ("Narration Prefix", self.narration_prefix_input),
            ("Tally HTTP URL", self.tally_url_input),
        ]
        self.form_labels: dict[str, QLabel] = {}
        for row, (label_text, widget) in enumerate(fields):
            label = QLabel(label_text)
            label.setObjectName("formLabel")
            self.form_labels[label_text] = label
            grid.addWidget(label, row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.load_masters_button = AppButton("Load Masters", "secondary", "LM", "#2563eb")
        self.load_masters_button.clicked.connect(self.load_tally_masters)
        self.preview_button = AppButton("Preview Entries", "primary", "PR", "#be123c")
        self.preview_button.clicked.connect(self.preview_random_sales)
        action_row.addWidget(self.load_masters_button)
        action_row.addWidget(self.preview_button)
        layout.addLayout(action_row)

        second_row = QHBoxLayout()
        second_row.setSpacing(8)
        self.import_button = AppButton("Import to Tally", "primary", "IM", "#0f766e")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_preview_to_tally)
        self.clear_button = AppButton("Clear Preview", "secondary", "CL", "#475467")
        self.clear_button.clicked.connect(self.clear_preview)
        second_row.addWidget(self.import_button)
        second_row.addWidget(self.clear_button)
        layout.addLayout(second_row)

        self.add_import_progress(layout)

        self.form_hint = QLabel("Preview pehle banega, import uske baad enable hoga.")
        self.form_hint.setObjectName("smallText")
        self.form_hint.setWordWrap(True)
        layout.addWidget(self.form_hint)
        self.sale_against_input.currentIndexChanged.connect(self.update_sale_against_mode)
        self.update_sale_against_mode()
        layout.addStretch()
        return panel

    def add_import_progress(self, layout: QVBoxLayout):
        progress_card = QFrame()
        progress_card.setObjectName("salesProgressPanel")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(7)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.progress_label = QLabel("Import ready")
        self.progress_label.setObjectName("progressTitle")
        self.progress_time_label = QLabel("Elapsed 00:00 | Remaining --:--")
        self.progress_time_label.setObjectName("smallText")
        top_row.addWidget(self.progress_label)
        top_row.addStretch()
        top_row.addWidget(self.progress_time_label)
        progress_layout.addLayout(top_row)

        self.import_progress = QProgressBar()
        self.import_progress.setObjectName("salesImportProgress")
        self.import_progress.setTextVisible(True)
        self.import_progress.setFormat("%p%")
        self.import_progress.setRange(0, 1)
        self.import_progress.setValue(0)
        progress_layout.addWidget(self.import_progress)

        self.progress_detail_label = QLabel("Preview ke baad import timing yahan display hogi.")
        self.progress_detail_label.setObjectName("smallText")
        self.progress_detail_label.setWordWrap(True)
        progress_layout.addWidget(self.progress_detail_label)

        layout.addWidget(progress_card)

    def preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("sectionTitle")
        self.total_label = QLabel("0 entries | taxable 0.00 | amount 0.00")
        self.total_label.setObjectName("smallText")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.total_label)
        layout.addLayout(header)

        self.table = QTableWidget(0, 10)
        self.table.setObjectName("salesTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Bill #",
                "Date",
                "Party",
                "Stock",
                "Taxable",
                "CGST",
                "SGST",
                "Round Off",
                "Amount",
                "Narration",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(4, 9):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        return panel

    def line_edit(self, value: str = "") -> QLineEdit:
        edit = QLineEdit(value)
        edit.setObjectName("searchBox")
        return edit

    def master_combo(self, value: str, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("masterCombo")
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(18)
        combo.addItem(value)
        combo.setCurrentText(value)

        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(placeholder)
            line_edit.setClearButtonEnabled(True)

        completer = combo.completer()
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        return combo

    def date_edit(self, value: QDate) -> QDateEdit:
        edit = QDateEdit(value)
        edit.setObjectName("dateInput")
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        return edit

    def text(self, field: QLineEdit | QComboBox) -> str:
        if isinstance(field, QComboBox):
            return field.currentText().strip()
        return field.text().strip()

    def parse_decimal(self, field: QLineEdit, label: str) -> Decimal:
        raw_value = self.text(field).replace(",", "")
        if not raw_value:
            raise ValueError(f"{label} required hai.")
        try:
            value = Decimal(raw_value).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{label} valid amount hona chahiye.") from exc
        if value <= Decimal("0.00"):
            raise ValueError(f"{label} zero se bada hona chahiye.")
        return value

    def form_data(self) -> dict:
        sale_against = self.sale_against_input.currentData()
        values = {
            "party_name": self.text(self.party_name_input) if sale_against == "party" else "",
            "cash_bank_ledger": self.text(self.cash_bank_ledger_input) if sale_against == "cash_bank" else "",
            "sale_ledger": self.text(self.sale_ledger_input),
            "voucher_type": self.text(self.voucher_type_input),
            "stock_item_name": self.text(self.stock_item_name_input),
            "cgst_ledger": self.text(self.cgst_ledger_input),
            "sgst_ledger": self.text(self.sgst_ledger_input),
            "round_off_ledger": self.text(self.round_off_ledger_input),
            "narration_prefix": self.text(self.narration_prefix_input),
        }
        missing = [name.replace("_", " ").title() for name in self.REQUIRED_FIELDS if not values[name]]
        if missing:
            raise ValueError(f"{', '.join(missing)} required hai.")

        if sale_against == "party" and not values["party_name"]:
            raise ValueError("Party Name required hai.")
        if sale_against == "cash_bank" and not values["cash_bank_ledger"]:
            raise ValueError("Cash / Bank Ledger required hai.")

        if self.master_value_lookups:
            if sale_against == "party":
                self.validate_master_value(values["party_name"], "party", "Party Name")
            else:
                self.validate_master_value(values["cash_bank_ledger"], "cash_bank", "Cash / Bank Ledger")
            for field_name, master_type, label in (
                ("sale_ledger", "sales", "Sales Ledger"),
                ("cgst_ledger", "cgst", "CGST Ledger"),
                ("sgst_ledger", "sgst", "SGST Ledger"),
                ("round_off_ledger", "round_off", "Round Off Ledger"),
            ):
                self.validate_master_value(values[field_name], master_type, label)
            self.validate_master_value(values["voucher_type"], "voucher_type", "Voucher Type")
            self.validate_master_value(values["stock_item_name"], "stock_item", "Stock Item Name")

        stock_gst_rates = self.stock_item_gst_rates.get(values["stock_item_name"].casefold())
        values["cgst_rate"] = stock_gst_rates[0] if stock_gst_rates is not None else None
        values["sgst_rate"] = stock_gst_rates[1] if stock_gst_rates is not None else None

        from_date = qdate_to_date(self.from_date_input.date())
        to_date = qdate_to_date(self.to_date_input.date())
        if from_date > to_date:
            raise ValueError("To Date, From Date ke baad ya same honi chahiye.")

        number_of_bills = self.bill_count_input.value()
        min_amount = self.parse_decimal(self.min_amount_input, "Minimum Amount")
        max_amount = self.parse_decimal(self.max_amount_input, "Maximum Amount")
        taxable_amount = self.parse_decimal(self.taxable_amount_input, "Total Taxable Amount")
        if min_amount > max_amount:
            raise ValueError("Maximum Amount, Minimum Amount se bada hona chahiye.")

        min_total = min_amount * number_of_bills
        max_total = max_amount * number_of_bills
        if taxable_amount < min_total or taxable_amount > max_total:
            raise ValueError(
                "Total Taxable Amount selected bill count ke range se bahar hai. "
                f"Allowed total {min_total} se {max_total} ke beech hai."
            )
        if number_of_bills > 1 and taxable_amount in {min_total, max_total}:
            if taxable_amount == min_total:
                reason = f"har bill Minimum Amount {min_amount:.2f} ka hi banega"
                suggestion = "Total Taxable Amount badhayein ya Minimum Amount kam karein."
            else:
                reason = f"har bill Maximum Amount {max_amount:.2f} ka hi banega"
                suggestion = "Total Taxable Amount ghatayein ya Maximum Amount badhayein."
            raise RandomCalculationNotPossibleError(
                f"Random calculation possible nahi hai, kyunki {reason}. {suggestion}"
            )

        values.update(
            {
                "from_date": from_date,
                "to_date": to_date,
                "number_of_bills": number_of_bills,
                "taxable_amount": taxable_amount,
                "min_amount": min_amount,
                "max_amount": max_amount,
            }
        )
        return values

    def update_sale_against_mode(self):
        party_mode = self.sale_against_input.currentData() == "party"
        self.form_labels["Party Name"].setVisible(party_mode)
        self.party_name_input.setVisible(party_mode)
        self.form_labels["Cash / Bank Ledger"].setVisible(not party_mode)
        self.cash_bank_ledger_input.setVisible(not party_mode)

        if party_mode:
            self.select_combo_value(self.cash_bank_ledger_input, "")
        else:
            self.select_combo_value(self.party_name_input, "")

        if hasattr(self, "form_hint"):
            mode_text = "Party ledger" if party_mode else "Cash / Bank ledger"
            self.set_status("info", f"{mode_text} mode selected. Sirf visible ledger voucher me use hoga.")

    def preview_random_sales(self):
        try:
            data = self.form_data()
            self.preview_entries = build_random_sale_preview_entries(**data)
        except RandomCalculationNotPossibleError as exc:
            message = str(exc)
            self.clear_preview()
            self.set_status("warning", message)
            QMessageBox.warning(self, "Random Calculation Not Possible", message)
            return
        except Exception as exc:
            self.set_status("error", str(exc))
            return

        self.populate_preview()
        self.import_button.setEnabled(bool(self.preview_entries))
        self.set_status("ok", f"{len(self.preview_entries)} entries previewed. Review karke import karein.")

    def populate_preview(self):
        self.table.setRowCount(len(self.preview_entries))
        total_taxable = Decimal("0.00")
        total_amount = Decimal("0.00")
        for row, entry in enumerate(self.preview_entries):
            total_taxable += Decimal(entry["taxable_amount"])
            total_amount += Decimal(entry["amount"])
            values = [
                str(entry["bill_number"]),
                entry["voucher_date"].isoformat() if isinstance(entry["voucher_date"], date) else str(entry["voucher_date"]),
                entry["party_name"],
                entry["stock_item_name"],
                money_text(entry["taxable_amount"]),
                money_text(entry["cgst_amount"]),
                money_text(entry["sgst_amount"]),
                money_text(entry["round_off_amount"]),
                money_text(entry["amount"]),
                entry["narration"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {0, 4, 5, 6, 7, 8}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)

        self.total_label.setText(
            f"{len(self.preview_entries)} entries | taxable {money_text(total_taxable)} | amount {money_text(total_amount)}"
        )

    def clear_preview(self):
        if self.import_worker and self.import_worker.isRunning():
            self.set_status("warning", "Import chal raha hai. Complete hone ke baad preview clear karein.")
            return
        self.preview_entries = []
        self.table.setRowCount(0)
        self.total_label.setText("0 entries | taxable 0.00 | amount 0.00")
        self.import_button.setEnabled(False)
        self.reset_import_progress()
        self.set_status("info", "Preview cleared")

    def load_tally_masters(self):
        tally_url = self.text(self.tally_url_input) or DEFAULT_TALLY_URL
        self.set_busy(True, "Loading Tally masters and ledger groups...")
        try:
            ledger_masters = fetch_tally_ledger_masters(tally_url)
            group_masters = fetch_tally_groups(tally_url)
            voucher_types = fetch_tally_voucher_types(tally_url)
            stock_item_masters = fetch_tally_stock_item_masters(tally_url)
        except Exception as exc:
            self.set_status("warning", f"Tally masters load nahi hue: {exc}")
            self.set_busy(False)
            return

        stock_items = [master.name for master in stock_item_masters]
        self.stock_item_gst_rates = {
            master.name.casefold(): (master.cgst_rate, master.sgst_rate, master.igst_rate)
            for master in stock_item_masters
        }

        party_ledgers = filter_tally_ledger_names_by_groups(
            ledger_masters,
            group_masters,
            ("Sundry Debtors",),
        )
        cash_bank_ledgers = filter_tally_ledger_names_by_groups(
            ledger_masters,
            group_masters,
            ("Cash-in-Hand", "Bank Accounts", "Bank OD A/c", "Bank OCC A/c"),
        )
        sales_ledgers = filter_tally_ledger_names_by_groups(
            ledger_masters,
            group_masters,
            ("Sales Accounts",),
        )
        tax_ledgers = filter_tally_ledger_names_by_groups(
            ledger_masters,
            group_masters,
            ("Duties & Taxes",),
        )
        cgst_ledgers = tax_ledgers
        sgst_ledgers = tax_ledgers
        indirect_ledgers = filter_tally_ledger_names_by_groups(
            ledger_masters,
            group_masters,
            ("Indirect Expenses", "Indirect Incomes"),
        )
        round_off_ledgers = self.keyword_ledgers(
            indirect_ledgers,
            ("round", "rounding", "r/off"),
        )
        if not round_off_ledgers:
            round_off_ledgers = self.keyword_ledgers(
                [master.name for master in ledger_masters],
                ("round", "rounding", "r/off"),
            )

        self.master_value_lookups = {
            "party": {value.casefold() for value in party_ledgers},
            "cash_bank": {value.casefold() for value in cash_bank_ledgers},
            "sales": {value.casefold() for value in sales_ledgers},
            "cgst": {value.casefold() for value in cgst_ledgers},
            "sgst": {value.casefold() for value in sgst_ledgers},
            "round_off": {value.casefold() for value in round_off_ledgers},
            "voucher_type": {value.strip().casefold() for value in voucher_types if value and value.strip()},
            "stock_item": {value.strip().casefold() for value in stock_items if value and value.strip()},
        }

        self.populate_master_combos([self.party_name_input], party_ledgers, allow_blank=True)
        self.populate_master_combos([self.cash_bank_ledger_input], cash_bank_ledgers, allow_blank=True)
        self.populate_master_combos([self.sale_ledger_input], sales_ledgers, allow_blank=True)
        self.populate_master_combos([self.cgst_ledger_input], cgst_ledgers, allow_blank=True)
        self.populate_master_combos([self.sgst_ledger_input], sgst_ledgers, allow_blank=True)
        self.populate_master_combos([self.round_off_ledger_input], round_off_ledgers, allow_blank=True)
        self.populate_master_combos([self.voucher_type_input], voucher_types)
        self.populate_master_combos([self.stock_item_name_input], stock_items)
        self.suggest_gst_ledgers_for_stock_item(self.text(self.stock_item_name_input))

        missing_required_groups: list[str] = []
        if not party_ledgers:
            missing_required_groups.append("Sundry Debtors")
        if not cash_bank_ledgers:
            missing_required_groups.append("Cash / Bank")
        if not sales_ledgers:
            missing_required_groups.append("Sales Accounts")
        status = "warning" if missing_required_groups else "ok"
        missing_text = (
            f" Missing required groups: {', '.join(missing_required_groups)}."
            if missing_required_groups
            else ""
        )
        self.set_status(
            status,
            f"Loaded {len(ledger_masters)} ledgers by group: party {len(party_ledgers)}, "
            f"cash/bank {len(cash_bank_ledgers)}, sales {len(sales_ledgers)}, tax {len(tax_ledgers)}, "
            f"round-off {len(round_off_ledgers)}. List se relevant ledger select karein.{missing_text}",
        )
        self.set_busy(False)

    def suggest_gst_ledgers_for_stock_item(self, stock_item_name: str):
        rates = self.stock_item_gst_rates.get(stock_item_name.strip().casefold())
        if rates is None:
            return

        cgst_rate, sgst_rate, igst_rate = rates
        if cgst_rate <= Decimal("0.00") and sgst_rate <= Decimal("0.00"):
            self.select_combo_value(self.cgst_ledger_input, "")
            self.select_combo_value(self.sgst_ledger_input, "")
            self.set_status("info", f"{stock_item_name}: Nil/0% GST. Tax ledgers clear kar diye gaye.")
            return

        cgst_ledger = self.match_gst_ledger(self.cgst_ledger_input, "cgst", cgst_rate)
        sgst_ledger = self.match_gst_ledger(self.sgst_ledger_input, "sgst", sgst_rate)
        self.select_combo_value(self.cgst_ledger_input, cgst_ledger)
        self.select_combo_value(self.sgst_ledger_input, sgst_ledger)

        total_rate = igst_rate if igst_rate > Decimal("0.00") else cgst_rate + sgst_rate
        rate_text = f"{total_rate.normalize():f}% GST = {cgst_rate.normalize():f}% CGST + {sgst_rate.normalize():f}% SGST"
        if cgst_ledger and sgst_ledger:
            self.set_status(
                "ok",
                f"{stock_item_name}: {rate_text}. Suggested {cgst_ledger} and {sgst_ledger}.",
            )
        else:
            missing = []
            if not cgst_ledger:
                missing.append(f"CGST {cgst_rate.normalize():f}%")
            if not sgst_ledger:
                missing.append(f"SGST {sgst_rate.normalize():f}%")
            self.set_status(
                "warning",
                f"{stock_item_name}: {rate_text}. Matching {', '.join(missing)} ledger nahi mila.",
            )

    def match_gst_ledger(self, combo: QComboBox, component: str, rate: Decimal) -> str:
        matches: list[str] = []
        for index in range(combo.count()):
            ledger = combo.itemText(index).strip()
            compact_name = re.sub(r"[^a-z]", "", ledger.casefold())
            if not ledger or component not in compact_name:
                continue
            ledger_rate = extract_gst_rate_from_stock_item_name(ledger)
            if ledger_rate == Decimal(rate).quantize(Decimal("0.01")):
                matches.append(ledger)
        matches.sort(key=lambda ledger: ("output" not in ledger.casefold(), ledger.casefold()))
        return matches[0] if matches else ""

    def select_combo_value(self, combo: QComboBox, value: str):
        index = combo.findText(value, Qt.MatchFlag.MatchFixedString) if value else -1
        if index >= 0:
            combo.setCurrentIndex(index)
        elif combo.count() and not combo.itemText(0):
            combo.setCurrentIndex(0)
        else:
            combo.setCurrentIndex(-1)

    def keyword_ledgers(self, ledgers: list[str], keywords: tuple[str, ...]) -> list[str]:
        return [
            ledger
            for ledger in ledgers
            if any(keyword in ledger.casefold() for keyword in keywords)
        ]

    def validate_master_value(self, value: str, master_type: str, label: str):
        if not value:
            return
        if value.casefold() not in self.master_value_lookups.get(master_type, set()):
            raise ValueError(f"{label} Tally ki fetched list se select karein.")

    def populate_master_combos(
        self,
        fields: list[QComboBox],
        values: list[str],
        *,
        allow_blank: bool = False,
    ):
        unique_values = sorted(
            {value.strip() for value in values if value and value.strip()},
            key=str.casefold,
        )
        value_lookup = {value.casefold(): index for index, value in enumerate(unique_values)}

        for field in fields:
            current_value = self.text(field)
            field.blockSignals(True)
            field.clear()
            if allow_blank:
                field.addItem("")
            field.addItems(unique_values)

            matched_index = value_lookup.get(current_value.casefold())
            if matched_index is not None:
                field.setCurrentIndex(matched_index + (1 if allow_blank else 0))
            else:
                field.setCurrentIndex(0 if allow_blank and field.count() else -1)
            field.blockSignals(False)

    def import_preview_to_tally(self):
        if not self.preview_entries:
            self.set_status("warning", "Preview pehle generate karein.")
            return
        if self.import_worker and self.import_worker.isRunning():
            self.set_status("warning", "Sales import already running hai.")
            return

        tally_url = self.text(self.tally_url_input) or DEFAULT_TALLY_URL
        total = len(self.preview_entries)
        self.import_started_at = time.monotonic()
        self.import_progress_current = 0
        self.import_progress_total = total
        self.import_created = 0
        self.import_failed = 0
        self.import_progress.setRange(0, total)
        self.import_progress.setValue(0)
        self.import_progress.setFormat("0%")
        self.progress_label.setText(f"Importing 0/{total} sale entries")
        self.progress_time_label.setText("Elapsed 00:00 | Remaining calculating...")
        self.progress_detail_label.setText("Tally response speed ke basis par remaining time estimate hoga.")
        self.set_busy(True, "Importing sale entries to Tally...")
        self.import_timer.start()
        self.import_worker = SalesImportWorker(tally_url, list(self.preview_entries))
        self.import_worker.progress.connect(self.handle_import_progress)
        self.import_worker.completed.connect(self.handle_import_completed)
        self.import_worker.finished.connect(self.handle_import_thread_finished)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.import_worker.start()

    def handle_import_progress(
        self,
        current: int,
        total: int,
        created: int,
        failed: int,
        elapsed: float,
        remaining: float,
    ):
        self.import_progress_current = current
        self.import_progress_total = total
        self.import_created = created
        self.import_failed = failed
        self.import_progress.setRange(0, max(total, 1))
        self.import_progress.setValue(current)
        percent = int((current / total) * 100) if total else 0
        self.import_progress.setFormat(f"{percent}%")
        self.progress_label.setText(f"Importing {current}/{total} sale entries")
        self.progress_time_label.setText(
            f"Elapsed {format_duration(elapsed)} | Remaining {format_duration(remaining)}"
        )
        self.progress_detail_label.setText(
            f"Created {created}, failed {failed}. Estimate current Tally speed ke basis par hai."
        )

    def refresh_import_timer(self):
        if not self.import_started_at or not self.import_progress_total:
            return
        elapsed = time.monotonic() - self.import_started_at
        if self.import_progress_current:
            remaining = (elapsed / self.import_progress_current) * (
                self.import_progress_total - self.import_progress_current
            )
            remaining_text = format_duration(remaining)
        else:
            remaining_text = "calculating..."
        self.progress_time_label.setText(
            f"Elapsed {format_duration(elapsed)} | Remaining {remaining_text}"
        )

    def handle_import_completed(self, created: int, failed: int, failed_entries: list, first_error: str):
        self.import_timer.stop()
        total = created + failed
        self.preview_entries = failed_entries
        self.populate_preview()
        self.import_button.setEnabled(bool(self.preview_entries))
        self.set_busy(False)
        self.import_progress.setRange(0, max(total, 1))
        self.import_progress.setValue(total)
        self.import_progress.setFormat("100%")
        elapsed = time.monotonic() - self.import_started_at if self.import_started_at else 0.0
        self.progress_time_label.setText(f"Elapsed {format_duration(elapsed)} | Remaining 00:00")
        self.progress_label.setText(f"Import completed: {created}/{total} created")
        if failed:
            self.progress_detail_label.setText(f"Created {created}, failed {failed}. Failed entries preview me bachi hain.")
            self.set_status("warning", f"Imported {created}. Failed {failed}. {first_error}")
        else:
            self.progress_detail_label.setText(f"All {created} sale vouchers Tally me create ho gaye.")
            self.set_status("ok", f"All {created} sale vouchers imported successfully.")

    def handle_import_thread_finished(self):
        self.import_timer.stop()
        self.import_worker = None

    def reset_import_progress(self):
        self.import_timer.stop()
        self.import_started_at = 0.0
        self.import_progress_current = 0
        self.import_progress_total = 0
        self.import_created = 0
        self.import_failed = 0
        self.import_progress.setRange(0, 1)
        self.import_progress.setValue(0)
        self.import_progress.setFormat("%p%")
        self.progress_label.setText("Import ready")
        self.progress_time_label.setText("Elapsed 00:00 | Remaining --:--")
        self.progress_detail_label.setText("Preview ke baad import timing yahan display hogi.")

    def set_busy(self, busy: bool, message: str | None = None):
        self.load_masters_button.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.import_button.setEnabled((not busy) and bool(self.preview_entries))
        self.clear_button.setEnabled(not busy)
        if message:
            self.set_status("info", message)

    def set_status(self, status: str, message: str):
        self.status_chip.set_status(status, message)
        self.form_hint.setText(message)


class FixedSalePanel(RandomSalePanel):
    REQUIRED_FIELDS = (
        "sale_ledger",
        "voucher_type",
        "stock_item_name",
    )

    def __init__(self, back_handler):
        self.excel_file_path = ""
        super().__init__(back_handler)

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Fixed Sale")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Excel rows se exact amount wali sale entries preview karke Tally me import karein.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack, 1)
        self.status_chip = StatusChip("Ready", "info")
        layout.addWidget(self.status_chip)
        back_button = AppButton("Back", "secondary", "BA", "#475467")
        back_button.clicked.connect(self.back_handler)
        layout.addWidget(back_button)
        return header

    def form_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("formPanel")
        panel.setFixedWidth(440)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Fixed Sale Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self.select_excel_button = AppButton("Select Excel", "primary", "XL", "#2563eb")
        self.select_excel_button.clicked.connect(self.select_excel_file)
        self.file_label = QLabel("No file selected")
        self.file_label.setObjectName("smallText")
        self.file_label.setWordWrap(True)
        file_row.addWidget(self.select_excel_button)
        file_row.addWidget(self.file_label, 1)
        layout.addLayout(file_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.sale_against_input = QComboBox()
        self.sale_against_input.setObjectName("masterCombo")
        self.sale_against_input.addItem("Cash / Bank Sale", "cash_bank")
        self.sale_against_input.addItem("Party Sale", "party")
        self.party_name_input = self.master_combo("ABC Traders", "Select party ledger from Tally")
        self.cash_bank_ledger_input = self.master_combo("Cash", "Select cash / bank ledger from Tally")
        self.sale_ledger_input = self.master_combo("Sales", "Select sales ledger from Tally")
        self.voucher_type_input = self.master_combo("Sales", "Select voucher type from Tally")
        self.stock_item_name_input = self.master_combo("18 % Item", "Select stock item from Tally")
        self.cgst_ledger_input = self.master_combo("Output CGST", "Optional CGST ledger")
        self.sgst_ledger_input = self.master_combo("Output SGST", "Optional SGST ledger")
        self.round_off_ledger_input = self.master_combo("Round Off", "Optional round-off ledger")
        self.narration_prefix_input = self.line_edit("")
        self.more_rate_input = self.line_edit("")
        self.more_quantity_input = self.line_edit("")
        self.tally_url_input = self.line_edit(DEFAULT_TALLY_URL)
        self.stock_item_name_input.currentTextChanged.connect(self.suggest_gst_ledgers_for_stock_item)

        fields = [
            ("Sale Against", self.sale_against_input),
            ("Party Name", self.party_name_input),
            ("Cash / Bank Ledger", self.cash_bank_ledger_input),
            ("Sales Ledger", self.sale_ledger_input),
            ("Voucher Type", self.voucher_type_input),
            ("Stock Item Name", self.stock_item_name_input),
            ("CGST Ledger", self.cgst_ledger_input),
            ("SGST Ledger", self.sgst_ledger_input),
            ("Round Off Ledger", self.round_off_ledger_input),
            ("Narration Prefix", self.narration_prefix_input),
            ("More Rate", self.more_rate_input),
            ("More Quantity", self.more_quantity_input),
            ("Tally HTTP URL", self.tally_url_input),
        ]
        self.form_labels: dict[str, QLabel] = {}
        for row, (label_text, widget) in enumerate(fields):
            label = QLabel(label_text)
            label.setObjectName("formLabel")
            self.form_labels[label_text] = label
            grid.addWidget(label, row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.load_masters_button = AppButton("Load Masters", "secondary", "LM", "#2563eb")
        self.load_masters_button.clicked.connect(self.load_tally_masters)
        self.preview_button = AppButton("Preview Entries", "primary", "PR", "#be123c")
        self.preview_button.clicked.connect(self.preview_fixed_sales)
        action_row.addWidget(self.load_masters_button)
        action_row.addWidget(self.preview_button)
        layout.addLayout(action_row)

        second_row = QHBoxLayout()
        second_row.setSpacing(8)
        self.import_button = AppButton("Import to Tally", "primary", "IM", "#0f766e")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_preview_to_tally)
        self.clear_button = AppButton("Clear Preview", "secondary", "CL", "#475467")
        self.clear_button.clicked.connect(self.clear_preview)
        second_row.addWidget(self.import_button)
        second_row.addWidget(self.clear_button)
        layout.addLayout(second_row)

        self.add_import_progress(layout)

        self.form_hint = QLabel("Excel me Date + Amount ya Date + Particulars + Narration + Debit/Credit format chalega.")
        self.form_hint.setObjectName("smallText")
        self.form_hint.setWordWrap(True)
        layout.addWidget(self.form_hint)
        self.sale_against_input.currentIndexChanged.connect(self.update_sale_against_mode)
        self.update_sale_against_mode()
        layout.addStretch()
        return panel

    def preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("sectionTitle")
        self.total_label = QLabel("0 entries | taxable 0.00 | amount 0.00")
        self.total_label.setObjectName("smallText")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.total_label)
        layout.addLayout(header)

        self.table = QTableWidget(0, 12)
        self.table.setObjectName("salesTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Bill #",
                "Date",
                "Party",
                "Stock",
                "Qty",
                "Rate",
                "Taxable",
                "CGST",
                "SGST",
                "Round Off",
                "Amount",
                "Narration",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for column in range(0, 11):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        return panel

    def select_excel_file(self):
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select Fixed Sale Excel",
            "",
            "Excel files (*.xlsx)",
        )
        if not file_path:
            return
        self.excel_file_path = file_path
        self.file_label.setText(file_path)
        self.set_status("info", "Excel selected. Preview Entries dabayein.")

    def form_data(self) -> dict:
        sale_against = self.sale_against_input.currentData()
        values = {
            "party_name": self.text(self.party_name_input) if sale_against == "party" else "",
            "cash_bank_ledger": self.text(self.cash_bank_ledger_input) if sale_against == "cash_bank" else "",
            "sale_ledger": self.text(self.sale_ledger_input),
            "voucher_type": self.text(self.voucher_type_input),
            "stock_item_name": self.text(self.stock_item_name_input),
            "cgst_ledger": self.text(self.cgst_ledger_input),
            "sgst_ledger": self.text(self.sgst_ledger_input),
            "round_off_ledger": self.text(self.round_off_ledger_input),
            "narration_prefix": self.text(self.narration_prefix_input),
        }
        missing = [name.replace("_", " ").title() for name in self.REQUIRED_FIELDS if not values[name]]
        if missing:
            raise ValueError(f"{', '.join(missing)} required hai.")
        if sale_against == "party" and not values["party_name"]:
            raise ValueError("Party Name required hai.")
        if sale_against == "cash_bank" and not values["cash_bank_ledger"]:
            raise ValueError("Cash / Bank Ledger required hai.")

        if self.master_value_lookups:
            if sale_against == "party":
                self.validate_master_value(values["party_name"], "party", "Party Name")
            else:
                self.validate_master_value(values["cash_bank_ledger"], "cash_bank", "Cash / Bank Ledger")
            for field_name, master_type, label in (
                ("sale_ledger", "sales", "Sales Ledger"),
                ("cgst_ledger", "cgst", "CGST Ledger"),
                ("sgst_ledger", "sgst", "SGST Ledger"),
                ("round_off_ledger", "round_off", "Round Off Ledger"),
            ):
                self.validate_master_value(values[field_name], master_type, label)
            self.validate_master_value(values["voucher_type"], "voucher_type", "Voucher Type")
            self.validate_master_value(values["stock_item_name"], "stock_item", "Stock Item Name")

        stock_gst_rates = self.stock_item_gst_rates.get(values["stock_item_name"].casefold())
        values["cgst_rate"] = stock_gst_rates[0] if stock_gst_rates is not None else None
        values["sgst_rate"] = stock_gst_rates[1] if stock_gst_rates is not None else None
        values["item_rate"] = self.parse_optional_decimal(self.more_rate_input, "More Rate", scale="0.0001")
        values["billed_quantity"] = self.parse_optional_decimal(
            self.more_quantity_input,
            "More Quantity",
            scale="0.001",
        )
        if values["billed_quantity"] is not None and values["item_rate"] is None:
            raise ValueError("More Quantity use karne ke liye More Rate bhi required hai.")
        return values

    def parse_optional_decimal(self, field: QLineEdit, label: str, *, scale: str) -> Decimal | None:
        raw_value = self.text(field).replace(",", "")
        if not raw_value:
            return None
        try:
            value = Decimal(raw_value).quantize(Decimal(scale))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{label} valid number hona chahiye.") from exc
        if value <= Decimal("0.00"):
            raise ValueError(f"{label} zero se bada hona chahiye.")
        return value

    def preview_fixed_sales(self):
        if not self.excel_file_path:
            self.set_status("warning", "Fixed Sale Excel file select karein.")
            return

        try:
            data = self.form_data()
            excel_rows = parse_fixed_sale_excel_rows(self.excel_file_path)
            self.preview_entries = build_fixed_sale_preview_entries(excel_rows, **data)
        except Exception as exc:
            self.set_status("error", str(exc))
            return

        self.populate_preview()
        self.import_button.setEnabled(bool(self.preview_entries))
        self.set_status("ok", f"{len(self.preview_entries)} fixed sale entries previewed. Review karke import karein.")

    def populate_preview(self):
        self.table.setRowCount(len(self.preview_entries))
        total_taxable = Decimal("0.00")
        total_amount = Decimal("0.00")
        for row, entry in enumerate(self.preview_entries):
            total_taxable += Decimal(entry["taxable_amount"])
            total_amount += Decimal(entry["amount"])
            values = [
                str(entry["bill_number"]),
                entry["voucher_date"].isoformat() if isinstance(entry["voucher_date"], date) else str(entry["voucher_date"]),
                entry["party_name"],
                entry["stock_item_name"],
                money_text(entry.get("billed_quantity")) if entry.get("billed_quantity") is not None else "-",
                money_text(entry.get("item_rate")) if entry.get("item_rate") is not None else "-",
                money_text(entry["taxable_amount"]),
                money_text(entry["cgst_amount"]),
                money_text(entry["sgst_amount"]),
                money_text(entry["round_off_amount"]),
                money_text(entry["amount"]),
                entry["narration"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {0, 4, 5, 6, 7, 8, 9, 10}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)

        self.total_label.setText(
            f"{len(self.preview_entries)} entries | taxable {money_text(total_taxable)} | amount {money_text(total_amount)}"
        )


def money_text(value) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def format_duration(seconds: float) -> str:
    if seconds < 0:
        return "--:--"
    total_seconds = max(0, int(round(seconds)))
    minutes, second = divmod(total_seconds, 60)
    hour, minute = divmod(minutes, 60)
    if hour:
        return f"{hour:02d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


def qdate_to_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())
