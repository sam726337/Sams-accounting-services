from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import APP_NAME, APP_VERSION, PRIVACY_URL, TERMS_URL
from sams_accounting_desktop.legal import PRIVACY_POLICY, TERMS_OF_USE
from sams_accounting_desktop.services.update_checker import UpdateInfo
from sams_accounting_desktop.state import start_local_trial, verify_license_details
from sams_accounting_desktop.ui.components import AppButton, StatusChip
from sams_accounting_desktop.ui.icons import logo_icon, logo_pixmap
from sams_accounting_desktop.ui.styles import STYLESHEET


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setObjectName("startupWindow")
        self.setWindowIcon(logo_icon(64))
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
        logo.setPixmap(logo_pixmap(62))
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


class LegalDocumentDialog(QDialog):
    def __init__(self, title: str, text: str, online_url: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.online_url = online_url
        self.setWindowTitle(title)
        self.setMinimumSize(760, 600)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)

        document = QTextBrowser()
        document.setObjectName("legalDocument")
        document.setPlainText(text)
        layout.addWidget(document, 1)

        buttons = QHBoxLayout()
        online = AppButton("View online", "secondary")
        online.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.online_url)))
        close = AppButton("Close", "primary")
        close.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(online)
        buttons.addWidget(close)
        layout.addLayout(buttons)


class LicenseWindow(QWidget):
    accepted = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} License")
        self.setObjectName("startupWindow")
        self.setWindowIcon(logo_icon(64))
        self.setMinimumSize(860, 650)
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
        logo.setPixmap(logo_pixmap(68))
        intro_layout.addWidget(logo)
        title = QLabel("License check")
        title.setObjectName("startupTitleLight")
        body = QLabel("Activate a signed licence or start a time-limited local trial. Review every accounting entry before posting to Tally.")
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

        self.name_input = QLineEdit()
        self.name_input.setObjectName("searchBox")
        self.name_input.setPlaceholderText("Name")
        form_layout.addWidget(self.field("Name", self.name_input))

        self.contact_input = QLineEdit()
        self.contact_input.setObjectName("searchBox")
        self.contact_input.setPlaceholderText("Email or mobile")
        form_layout.addWidget(self.field("Email or mobile", self.contact_input))

        self.license_input = QLineEdit()
        self.license_input.setObjectName("searchBox")
        self.license_input.setPlaceholderText("Paste your signed SAM1 licence key")
        form_layout.addWidget(self.field("License key", self.license_input))

        self.message = StatusChip("Enter details to continue.", "info")
        form_layout.addWidget(self.message)

        legal_actions = QHBoxLayout()
        terms_button = AppButton("View Terms", "secondary")
        terms_button.clicked.connect(lambda: self.open_legal("Terms of Use", TERMS_OF_USE, TERMS_URL))
        privacy_button = AppButton("View Privacy", "secondary")
        privacy_button.clicked.connect(lambda: self.open_legal("Privacy Policy", PRIVACY_POLICY, PRIVACY_URL))
        legal_actions.addWidget(terms_button)
        legal_actions.addWidget(privacy_button)
        form_layout.addLayout(legal_actions)

        self.terms_checkbox = QCheckBox("I have read and accept the Terms of Use.")
        self.terms_checkbox.setObjectName("consentCheckbox")
        self.privacy_checkbox = QCheckBox("I have read and accept the Privacy Policy.")
        self.privacy_checkbox.setObjectName("consentCheckbox")
        form_layout.addWidget(self.terms_checkbox)
        form_layout.addWidget(self.privacy_checkbox)

        self.verify_button = AppButton("Verify License", "primary", "OK", "#0f766e")
        self.verify_button.clicked.connect(self.verify_license)
        self.trial_button = AppButton("Start 14-Day Local Trial", "secondary", "TR", "#0f766e")
        self.trial_button.clicked.connect(self.continue_trial)
        form_layout.addWidget(self.verify_button)
        form_layout.addWidget(self.trial_button)
        self.terms_checkbox.toggled.connect(self.update_consent_buttons)
        self.privacy_checkbox.toggled.connect(self.update_consent_buttons)
        self.update_consent_buttons()
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
            terms_accepted=self.terms_checkbox.isChecked(),
            privacy_accepted=self.privacy_checkbox.isChecked(),
        )
        self.message.set_status("ok" if ok else "error", message)
        if ok:
            self.accepted.emit()

    def continue_trial(self):
        ok, message, _settings = start_local_trial(
            self.name_input.text(),
            self.contact_input.text(),
            terms_accepted=self.terms_checkbox.isChecked(),
            privacy_accepted=self.privacy_checkbox.isChecked(),
        )
        self.message.set_status("ok" if ok else "error", message)
        if ok:
            self.accepted.emit()

    def update_consent_buttons(self):
        enabled = self.terms_checkbox.isChecked() and self.privacy_checkbox.isChecked()
        self.verify_button.setEnabled(enabled)
        self.trial_button.setEnabled(enabled)
        if not enabled:
            self.message.set_status("info", "Review and accept both documents to continue.")

    def open_legal(self, title: str, text: str, online_url: str):
        dialog = LegalDocumentDialog(title, text, online_url, self)
        dialog.exec()


class UpdatePrompt(QWidget):
    accepted = Signal()

    def __init__(self, info: UpdateInfo, current_version: str):
        super().__init__()
        self.info = info
        self.setWindowTitle(f"{APP_NAME} Update")
        self.setObjectName("startupWindow")
        self.setWindowIcon(logo_icon(64))
        self.setMinimumSize(720, 460)
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
        logo.setPixmap(logo_pixmap(68))
        intro_layout.addWidget(logo)
        title = QLabel("Update available")
        title.setObjectName("startupTitleLight")
        intro_layout.addWidget(title)
        status = StatusChip("Mandatory update" if info.mandatory else "Optional update", "warning" if info.mandatory else "info")
        intro_layout.addWidget(status)
        intro_layout.addStretch()
        layout.addWidget(intro, 1)

        card = QFrame()
        card.setObjectName("startupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        heading = QLabel(f"{current_version} -> {info.latest_version}")
        heading.setObjectName("pageTitle")
        card_layout.addWidget(heading)

        notes = QLabel(info.release_notes or "New desktop update available.")
        notes.setObjectName("startupBody")
        notes.setWordWrap(True)
        card_layout.addWidget(notes)

        source = QLabel(f"Manifest: {info.source_url}")
        source.setObjectName("startupMeta")
        source.setWordWrap(True)
        card_layout.addWidget(source)

        download = AppButton("Download Installer", "primary", "DL", "#0f766e")
        download.clicked.connect(self.open_download)
        card_layout.addWidget(download)

        if not info.mandatory:
            later = AppButton("Continue This Version", "secondary", "GO", "#2563eb")
            later.clicked.connect(self.accepted.emit)
            card_layout.addWidget(later)
        else:
            locked = QLabel("Mandatory update hai. Installer download karke latest version install karein.")
            locked.setObjectName("startupBody")
            locked.setWordWrap(True)
            card_layout.addWidget(locked)

        card_layout.addStretch()
        layout.addWidget(card, 2)

    def open_download(self):
        QDesktopServices.openUrl(QUrl(self.info.download_url))
