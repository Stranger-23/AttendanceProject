"""Phase-one pages explicitly distinguish placeholders from empty live data."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from attendance_app.ui.components.cards import Card
from attendance_app.ui.components.icons import icon


class PlaceholderPage(QWidget):
    def __init__(self, key: str, title: str, description: str):
        super().__init__()
        self.setObjectName("page_" + key)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card()
        inner = QVBoxLayout(card)
        inner.setContentsMargins(24, 24, 24, 24)
        inner.setSpacing(16)
        inner.addStretch()
        symbol = QLabel()
        symbol.setProperty("role", "emptyIcon")
        symbol.setFixedSize(80, 80)
        symbol.setPixmap(icon(key, True).pixmap(32, 32))
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(symbol, 0, Qt.AlignmentFlag.AlignHCenter)
        heading = QLabel(title)
        heading.setProperty("role", "heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(heading)
        text = QLabel(description)
        text.setProperty("role", "muted")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(text)
        note = QLabel("این بخش در مرحله‌های بعدی پیاده‌سازی می‌شود.")
        note.setProperty("role", "footnote")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        inner.addWidget(note)
        inner.addStretch()
        layout.addWidget(card)
