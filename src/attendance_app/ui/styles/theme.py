"""Shared visual tokens and reusable widget states."""
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget
from pathlib import Path

PRIMARY = "#6C5CE7"
SECONDARY = "#777B84"
BACKGROUND = "#F7F8FA"
PRIMARY_DARK = "#5B4BD6"
PRIMARY_LIGHT = "#F0EDFF"
SURFACE = "#FFFFFF"
TEXT = "#111111"
BORDER = "#E4E6EA"

# Qt mirrors QPushButton text alignment in RTL: left anchors the icon/text at the right edge.
STYLESHEET = """
QWidget { color: #111111; }
QMainWindow, QWidget#workspace { background: #F7F8FA; }
QWidget#dashboard_content { background: #F7F8FA; }
QFrame#sidebar { background: white; border-left: 1px solid #E4E6EA; }
QFrame[card="true"] { background: white; border: 1px solid #E4E6EA; border-radius: 22px; }
QLabel { background: transparent; border: none; }
QLabel[role="muted"] { color: #777B84; font-size: 14px; }
QLabel[role="section"] { color: #777B84; font-size: 12px; font-weight: 500; }
QLabel[role="footnote"] { color: #777B84; font-size: 12px; }
QLabel[role="emptyIcon"] { background: #F0EDFF; border-radius: 24px; }
QLabel[role="title"] { font-size: 28px; font-weight: 700; }
QLabel[role="heading"] { font-size: 20px; font-weight: 700; }
QLabel[role="statValue"] { color: #6C5CE7; font-size: 30px; font-weight: 700; }
QLabel[role="brand"] { font-size: 18px; font-weight: 700; }
QLabel[role="badge"] { color: #6C5CE7; background: #F0EDFF; border-radius: 10px; padding: 8px 12px; font-size: 12px; font-weight: 500; }
QPushButton { background: white; border: 1px solid #E4E6EA; border-radius: 12px; padding: 12px 16px; min-height: 24px; }
QPushButton:hover { background: #F7F8FA; }
QPushButton:focus { border-color: #6C5CE7; }
QPushButton:pressed { background: #F0EDFF; border-color: #6C5CE7; }
QPushButton[variant="primary"] { background: #6C5CE7; color: white; border-color: #6C5CE7; }
QPushButton[variant="primary"]:hover, QPushButton[variant="primary"]:pressed { background: #5B4BD6; }
QPushButton[variant="primary"]:focus { border-color: #111111; }
QPushButton:disabled { background: #F1F3F5; color: #777B84; border-color: #E4E6EA; }
QPushButton[nav="true"] { text-align: left; color: #777B84; border: 2px solid transparent; padding: 0px 12px; min-height: 48px; max-height: 48px; }
QPushButton[nav="true"]:hover { background: #F7F8FA; }
QPushButton[nav="true"]:checked { background: #F0EDFF; color: #6C5CE7; font-weight: 600; }
QPushButton[nav="true"]:checked:hover { background: #F0EDFF; }
QPushButton[nav="true"]:focus { border-color: #6C5CE7; }
QLineEdit, QComboBox { background: white; border: 1px solid #E4E6EA; border-radius: 12px; padding: 12px; min-height: 24px; }
QLineEdit:focus, QComboBox:focus { border-color: #6C5CE7; }
QDialog, QWidget#dialog_content { background: #FFFFFF; }
QLabel[role="cameraPreview"] { background: #F7F8FA; border: 1px solid #E4E6EA; border-radius: 20px; }
QSpinBox { background: #FFFFFF; border: 1px solid #E4E6EA; border-radius: 10px; padding: 8px; min-height: 24px; }
QDateEdit { background: #FFFFFF; border: 1px solid #E4E6EA; border-radius: 10px; padding: 8px; min-height: 24px; }
QDateEdit:focus { border-color: #6C5CE7; }
QDateEdit:disabled { color: #777B84; background: #F7F8FA; }
QTextEdit { background: #FFFFFF; border: 1px solid #E4E6EA; border-radius: 12px; padding: 12px; }
QTextEdit:focus { border-color: #6C5CE7; }
QLabel[role="error"] { color: #E5484D; }
QTableView { background: #FFFFFF; border: none; selection-background-color: #F0EDFF; selection-color: #111111; }
QTableView::item { padding: 8px; border-bottom: 1px solid #E7E8EB; }
QTableView::item:focus { border: 1px solid #6C5CE7; }
QHeaderView::section { background: #F7F8FA; color: #777B84; border: none; border-bottom: 1px solid #E4E6EA; padding: 12px 8px; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: white; color: #111111; border: 1px solid #E4E6EA; padding: 8px; }
"""


def apply_theme(app: QApplication, font_dir: Path) -> str:
    families = []
    for name in ("IRANSans.ttf", "IRANSans_Medium.ttf", "IRANSans_Bold.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(font_dir / name))
        if font_id < 0:
            raise RuntimeError("بارگذاری قلم ایران‌سنس ناموفق بود: " + name)
        families.extend(QFontDatabase.applicationFontFamilies(font_id))
    family = families[0]
    font = QFont(family)
    font.setPixelSize(14)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)
    return family


def add_soft_shadow(widget: QWidget) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 10))
    widget.setGraphicsEffect(shadow)
