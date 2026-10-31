"""Shared attendance painting; the History presentation is preserved unchanged."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyledItemDelegate


class HistoryDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if index.column() in (1, 2, 3):
            option.direction = Qt.LayoutDirection.LeftToRight

    def paint(self, painter, option, index):
        if index.column() != 4:
            return super().paint(painter, option, index)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(12, 10, -12, -10)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#EAF7EF'))
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(QColor('#16834A'))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, 'حاضر')
        painter.restore()
