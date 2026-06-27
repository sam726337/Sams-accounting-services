from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.sales_generator import build_random_sale_preview_entries
from sams_accounting_desktop.services.tally_client import (
    create_tally_item_invoice_voucher,
    fetch_tally_ledgers,
    fetch_tally_stock_items,
    fetch_tally_voucher_types,
)
from sams_accounting_desktop.ui.components import AppButton, StatusChip
from sams_accounting_desktop.ui.icons import make_icon


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
        self.fixed_placeholder = self.build_fixed_placeholder()

        self.stack.addWidget(self.choice_page)
        self.stack.addWidget(self.random_sale_panel)
        self.stack.addWidget(self.fixed_placeholder)
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

    def build_fixed_placeholder(self) -> QWidget:
        page = QWidget()
        page.setObjectName("workspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("topbar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 12, 22, 12)
        title_stack = QVBoxLayout()
        title = QLabel("Fixed Sale")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Excel based fixed sale flow will use the same sales workspace.")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header_layout.addLayout(title_stack)
        header_layout.addStretch()
        back_button = AppButton("Back", "secondary", "BA", "#475467")
        back_button.clicked.connect(self.open_choices)
        header_layout.addWidget(back_button)
        layout.addWidget(header)
        layout.addWidget(StatusChip("Fixed Sale selected", "info"))
        layout.addStretch()
        return page

    def open_choices(self):
        self.stack.setCurrentWidget(self.choice_page)

    def open_random_sale(self):
        self.selection_status.set_status("warning", "Random Sale selected")
        self.stack.setCurrentWidget(self.random_sale_panel)

    def open_fixed_sale(self):
        self.selection_status.set_status("ok", "Fixed Sale selected")
        self.stack.setCurrentWidget(self.fixed_placeholder)


class RandomSalePanel(QWidget):
    REQUIRED_FIELDS = (
        "party_name",
        "cash_bank_ledger",
        "sale_ledger",
        "voucher_type",
        "stock_item_name",
    )

    def __init__(self, back_handler):
        super().__init__()
        self.setObjectName("workspace")
        self.back_handler = back_handler
        self.preview_entries: list[dict] = []
        self.completers: list[QCompleter] = []

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
        self.party_name_input = self.line_edit("ABC Traders")
        self.cash_bank_ledger_input = self.line_edit("Cash")
        self.sale_ledger_input = self.line_edit("Sales")
        self.voucher_type_input = self.line_edit("Sales")
        self.stock_item_name_input = self.line_edit("18 % Item")
        self.cgst_ledger_input = self.line_edit("Output CGST")
        self.sgst_ledger_input = self.line_edit("Output SGST")
        self.round_off_ledger_input = self.line_edit("Round Off")
        self.bill_count_input = QSpinBox()
        self.bill_count_input.setObjectName("numberInput")
        self.bill_count_input.setRange(1, 500)
        self.bill_count_input.setValue(10)
        self.min_amount_input = self.line_edit("100.00")
        self.max_amount_input = self.line_edit("10000.00")
        self.taxable_amount_input = self.line_edit("10000.00")
        self.narration_prefix_input = self.line_edit("Sale entry")
        self.tally_url_input = self.line_edit(DEFAULT_TALLY_URL)

        fields = [
            ("From Date", self.from_date_input),
            ("To Date", self.to_date_input),
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
        for row, (label_text, widget) in enumerate(fields):
            label = QLabel(label_text)
            label.setObjectName("formLabel")
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
        clear_button = AppButton("Clear Preview", "secondary", "CL", "#475467")
        clear_button.clicked.connect(self.clear_preview)
        second_row.addWidget(self.import_button)
        second_row.addWidget(clear_button)
        layout.addLayout(second_row)

        self.form_hint = QLabel("Preview pehle banega, import uske baad enable hoga.")
        self.form_hint.setObjectName("smallText")
        self.form_hint.setWordWrap(True)
        layout.addWidget(self.form_hint)
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

    def date_edit(self, value: QDate) -> QDateEdit:
        edit = QDateEdit(value)
        edit.setObjectName("dateInput")
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        return edit

    def text(self, field: QLineEdit) -> str:
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
        values = {
            "party_name": self.text(self.party_name_input),
            "cash_bank_ledger": self.text(self.cash_bank_ledger_input),
            "sale_ledger": self.text(self.sale_ledger_input),
            "voucher_type": self.text(self.voucher_type_input),
            "stock_item_name": self.text(self.stock_item_name_input),
            "cgst_ledger": self.text(self.cgst_ledger_input),
            "sgst_ledger": self.text(self.sgst_ledger_input),
            "round_off_ledger": self.text(self.round_off_ledger_input),
            "narration_prefix": self.text(self.narration_prefix_input) or "Sale entry",
        }
        missing = [name.replace("_", " ").title() for name in self.REQUIRED_FIELDS if not values[name]]
        if missing:
            raise ValueError(f"{', '.join(missing)} required hai.")

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

    def preview_random_sales(self):
        try:
            data = self.form_data()
            self.preview_entries = build_random_sale_preview_entries(**data)
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
        self.preview_entries = []
        self.table.setRowCount(0)
        self.total_label.setText("0 entries | taxable 0.00 | amount 0.00")
        self.import_button.setEnabled(False)
        self.set_status("info", "Preview cleared")

    def load_tally_masters(self):
        tally_url = self.text(self.tally_url_input) or DEFAULT_TALLY_URL
        self.set_busy(True, "Loading Tally masters...")
        try:
            ledgers = fetch_tally_ledgers(tally_url)
            voucher_types = fetch_tally_voucher_types(tally_url)
            stock_items = fetch_tally_stock_items(tally_url)
        except Exception as exc:
            self.set_status("warning", f"Tally masters load nahi hue: {exc}")
            self.set_busy(False)
            return

        self.apply_completer(
            [
                self.party_name_input,
                self.cash_bank_ledger_input,
                self.sale_ledger_input,
                self.cgst_ledger_input,
                self.sgst_ledger_input,
                self.round_off_ledger_input,
            ],
            ledgers,
        )
        self.apply_completer([self.voucher_type_input], voucher_types)
        self.apply_completer([self.stock_item_name_input], stock_items)
        self.set_status("ok", f"Loaded {len(ledgers)} ledgers, {len(voucher_types)} voucher types, {len(stock_items)} stock items.")
        self.set_busy(False)

    def apply_completer(self, fields: list[QLineEdit], values: list[str]):
        completer = QCompleter(values)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completers.append(completer)
        for field in fields:
            field.setCompleter(completer)

    def import_preview_to_tally(self):
        if not self.preview_entries:
            self.set_status("warning", "Preview pehle generate karein.")
            return

        tally_url = self.text(self.tally_url_input) or DEFAULT_TALLY_URL
        self.set_busy(True, "Importing to Tally...")
        created = 0
        failed = 0
        failed_entries: list[dict] = []
        first_error = ""
        for entry in self.preview_entries:
            try:
                result = create_tally_item_invoice_voucher(
                    tally_url,
                    voucher_type=entry.get("voucher_type") or "Sales",
                    voucher_date=entry["voucher_date"],
                    party_ledger=entry["cash_bank_ledger"],
                    sales_ledger=entry["sale_ledger"],
                    stock_item_name=entry["stock_item_name"],
                    taxable_amount=Decimal(entry["taxable_amount"]),
                    total_amount=Decimal(entry["amount"]),
                    cgst_ledger=entry.get("cgst_ledger", ""),
                    sgst_ledger=entry.get("sgst_ledger", ""),
                    round_off_ledger=entry.get("round_off_ledger", ""),
                    round_off_amount=Decimal(entry.get("round_off_amount", "0.00")),
                    narration=entry["narration"],
                    voucher_number=str(entry.get("bill_number", "")),
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

        self.preview_entries = failed_entries
        self.populate_preview()
        self.import_button.setEnabled(bool(self.preview_entries))
        self.set_busy(False)
        if failed:
            self.set_status("warning", f"Imported {created}. Failed {failed}. {first_error}")
        else:
            self.set_status("ok", f"All {created} sale vouchers imported successfully.")

    def set_busy(self, busy: bool, message: str | None = None):
        self.load_masters_button.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.import_button.setEnabled((not busy) and bool(self.preview_entries))
        if message:
            self.set_status("info", message)

    def set_status(self, status: str, message: str):
        self.status_chip.set_status(status, message)
        self.form_hint.setText(message)


def money_text(value) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def qdate_to_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())
