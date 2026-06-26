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
