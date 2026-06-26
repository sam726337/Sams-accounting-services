import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sams_accounting_desktop.config import APP_NAME
from sams_accounting_desktop.state import is_license_verified
from sams_accounting_desktop.ui.dashboard_window import DashboardWindow
from sams_accounting_desktop.ui.startup import LicenseWindow, SplashScreen


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    windows: dict[str, object] = {}

    def show_dashboard():
        window = DashboardWindow()
        windows["dashboard"] = window
        window.showMaximized()

    def show_license():
        license_window = LicenseWindow()
        windows["license"] = license_window

        def accept_license():
            license_window.close()
            show_dashboard()

        license_window.accepted.connect(accept_license)
        license_window.show()

    def route_after_splash():
        splash.set_status("Checking license...", "info")

        def open_next_screen():
            splash.close()
            if is_license_verified():
                show_dashboard()
            else:
                show_license()

        QTimer.singleShot(550, open_next_screen)

    splash = SplashScreen()
    windows["splash"] = splash
    splash.show()
    QTimer.singleShot(700, route_after_splash)

    sys.exit(app.exec())
