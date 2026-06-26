import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sams_accounting_desktop.config import APP_NAME
from sams_accounting_desktop.services.update_checker import check_for_update
from sams_accounting_desktop.state import is_license_verified
from sams_accounting_desktop.ui.dashboard_window import DashboardWindow
from sams_accounting_desktop.ui.startup import LicenseWindow, SplashScreen, UpdatePrompt


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

    def show_next_after_startup():
        if is_license_verified():
            show_dashboard()
        else:
            show_license()

    def route_after_splash():
        splash.set_status("Checking updates...", "info")

        def open_next_screen():
            result = check_for_update()
            if result.update_available and result.info is not None:
                splash.close()
                update_prompt = UpdatePrompt(result.info, result.current_version)
                windows["update"] = update_prompt

                def continue_after_update_prompt():
                    update_prompt.close()
                    show_next_after_startup()

                update_prompt.accepted.connect(continue_after_update_prompt)
                update_prompt.show()
                return

            splash.set_status("Checking license...", "info" if not result.error else "warning")
            QTimer.singleShot(350, open_license_or_dashboard)

        def open_license_or_dashboard():
            splash.close()
            show_next_after_startup()

        QTimer.singleShot(550, open_next_screen)

    splash = SplashScreen()
    windows["splash"] = splash
    splash.show()
    QTimer.singleShot(700, route_after_splash)

    sys.exit(app.exec())
