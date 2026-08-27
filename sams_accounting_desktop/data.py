from .models import Activity, Module


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
        "Sales",
        "Random sales invoice preview generate karke direct Tally me create karein.",
        "Invoice",
        "Generator",
        "#be123c",
        "SA",
    ),
    Module(
        "Purchase Reconciliation",
        "GST portal purchase Excel ko Tally purchase vouchers ke saath reconcile karein.",
        "GST",
        "Multi-file",
        "#15803d",
        "PR",
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
]


ACTIVITY = [
    Activity("Today", "Tally", "Company and masters sync ready", "Healthy"),
    Activity("Today", "Purchase Reconciliation", "Multiple GST Excel support enabled", "Ready"),
    Activity("Today", "Bank PDF", "Payment and Receipt posting workflow available", "Ready"),
    Activity("Today", "Sales", "Invoice preview generator available", "Ready"),
]
