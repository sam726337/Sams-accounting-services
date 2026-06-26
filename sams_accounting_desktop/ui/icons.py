from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap


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


def make_menu_icon(size: int = 28, color: str = "#0f766e") -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidth(max(2, size // 11))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    left = size * 0.24
    right = size * 0.76
    for y in (size * 0.32, size * 0.5, size * 0.68):
        painter.drawLine(int(left), int(y), int(right), int(y))
    painter.end()

    return QIcon(pixmap)
