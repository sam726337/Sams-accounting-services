import sys

from PySide6.QtWidgets import QApplication

from sams_accounting_desktop.config import APP_NAME
from sams_accounting_desktop.ui.dashboard_window import DashboardWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    window = DashboardWindow()
    window.showMaximized()

    sys.exit(app.exec())
