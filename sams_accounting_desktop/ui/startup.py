from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import APP_NAME, APP_VERSION
from sams_accounting_desktop.state import start_local_trial, verify_license_details
from sams_accounting_desktop.ui.components import AppButton, StatusChip
from sams_accounting_desktop.ui.icons import make_icon
from sams_accounting_desktop.ui.styles import STYLESHEET


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setObjectName("startupWindow")
        self.setWindowIcon(make_icon("SA", "#0f766e", 64))
        self.setFixedSize(560, 340)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        card = QFrame()
        card.setObjectName("startupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(make_icon("SA", "#0f766e", 58, 12).pixmap(58, 58))
        brand.addWidget(logo)
        brand_copy = QVBoxLayout()
        title = QLabel("Sams Accounting Desktop")
        title.setObjectName("startupTitle")
        subtitle = QLabel(f"{APP_VERSION} | Secure local accounting workspace")
        subtitle.setObjectName("startupSubtitle")
        brand_copy.addWidget(title)
        brand_copy.addWidget(subtitle)
        brand.addLayout(brand_copy, 1)
        card_layout.addLayout(brand)

        message = QLabel("Preparing dashboard, license state, and local workflow checks.")
        message.setObjectName("startupBody")
        message.setWordWrap(True)
        card_layout.addWidget(message)

        self.status = StatusChip("Starting...", "info")
        card_layout.addWidget(self.status)
        card_layout.addStretch()

        layout.addWidget(card)

    def set_status(self, text: str, status: str = "info"):
        self.status.set_status(status, text)


class LicenseWindow(QWidget):
    accepted = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} License")
        self.setObjectName("startupWindow")
        self.setWindowIcon(make_icon("SA", "#0f766e", 64))
        self.setMinimumSize(760, 500)
        self.setStyleSheet(STYLESHEET)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        intro = QFrame()
        intro.setObjectName("startupHero")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(26, 26, 26, 26)
        intro_layout.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(make_icon("SA", "#14b8a6", 64, 14).pixmap(64, 64))
        intro_layout.addWidget(logo)
        title = QLabel("License check")
        title.setObjectName("startupTitleLight")
        body = QLabel("Secure desktop access ke liye license verify karein. Demo testing ke liye SAM-DEMO key use kar sakte hain.")
        body.setObjectName("startupBodyLight")
        body.setWordWrap(True)
        intro_layout.addWidget(title)
        intro_layout.addWidget(body)
        intro_layout.addStretch()
        layout.addWidget(intro, 1)

        form = QFrame()
        form.setObjectName("startupCard")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(12)

        heading = QLabel("Activate workspace")
        heading.setObjectName("pageTitle")
        form_layout.addWidget(heading)

        self.name_input = QLineEdit("sameer mansuri")
        self.name_input.setObjectName("searchBox")
        self.name_input.setPlaceholderText("Name")
        form_layout.addWidget(self.field("Name", self.name_input))

        self.contact_input = QLineEdit()
        self.contact_input.setObjectName("searchBox")
        self.contact_input.setPlaceholderText("Email or mobile")
        form_layout.addWidget(self.field("Email or mobile", self.contact_input))

        self.license_input = QLineEdit("SAM-DEMO")
        self.license_input.setObjectName("searchBox")
        self.license_input.setPlaceholderText("SAM-DEMO or SAM-XXXX")
        form_layout.addWidget(self.field("License key", self.license_input))

        self.message = StatusChip("Enter details to continue.", "info")
        form_layout.addWidget(self.message)

        verify_button = AppButton("Verify License", "primary", "OK", "#0f766e")
        verify_button.clicked.connect(self.verify_license)
        trial_button = AppButton("Continue Local Trial", "secondary", "TR", "#2563eb")
        trial_button.clicked.connect(self.continue_trial)
        form_layout.addWidget(verify_button)
        form_layout.addWidget(trial_button)
        form_layout.addStretch()
        layout.addWidget(form, 1)

    def field(self, label_text: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("mutedLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def verify_license(self):
        ok, message, _settings = verify_license_details(
            self.name_input.text(),
            self.contact_input.text(),
            self.license_input.text(),
        )
        self.message.set_status("ok" if ok else "error", message)
        if ok:
            self.accepted.emit()

    def continue_trial(self):
        ok, message, _settings = start_local_trial(self.name_input.text(), self.contact_input.text())
        self.message.set_status("ok" if ok else "error", message)
        if ok:
            self.accepted.emit()
