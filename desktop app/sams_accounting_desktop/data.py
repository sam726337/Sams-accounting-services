from .models import Activity, Module


MODULES = [
    Module(
        "Tally",
        "Connect to Tally Prime and securely load company masters.",
        "Ready",
        "Connected",
        "#0f766e",
        "TA",
    ),
    Module(
        "Sales",
        "Generate, review, and post sales invoices directly to Tally.",
        "Invoice",
        "Generator",
        "#0f766e",
        "SA",
    ),
    Module(
        "Purchase Reconciliation",
        "Reconcile GST purchase files with vouchers recorded in Tally.",
        "GST",
        "Multi-file",
        "#0f766e",
        "PR",
    ),
    Module(
        "Excel",
        "Review bank rows, map ledgers, and import verified entries.",
        "0 files",
        "Waiting",
        "#0f766e",
        "XL",
    ),
    Module(
        "Bank PDF",
        "Parse statements into reviewable payment and receipt vouchers.",
        "Parser",
        "Available",
        "#0f766e",
        "BP",
    ),
    Module(
        "Image PDF",
        "Extract scanned statements, map ledgers, and prepare Tally posting.",
        "OCR",
        "Available",
        "#0f766e",
        "IP",
    ),
]


ACTIVITY = [
    Activity("Today", "Tally", "Company and masters sync ready", "Healthy"),
    Activity("Today", "Purchase Reconciliation", "Multiple GST Excel support enabled", "Ready"),
    Activity("Today", "Bank PDF", "Payment and Receipt posting workflow available", "Ready"),
    Activity("Today", "Sales", "Invoice preview generator available", "Ready"),
]
