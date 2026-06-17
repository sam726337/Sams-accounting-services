from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


def make_icon(text: str, color: str, size: int = 38, radius: int = 9) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", max(9, size // 4), QFont.Weight.DemiBold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()

    return QIcon(pixmap)
