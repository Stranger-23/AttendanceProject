from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from attendance_app.domain.people import normalize_search
from attendance_app.ui.formatting import attendance_date


class AttendanceTableModel(QAbstractTableModel):
    HEADERS = ('نام و نام خانوادگی', 'شناسه فرد', 'تاریخ حضور', 'ساعت حضور', 'وضعیت حضور')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.sort_column, self.sort_order = 2, Qt.SortOrder.DescendingOrder

    def replace(self, records):
        self.beginResetModel()
        self.records = list(records)
        self._sort()
        self.endResetModel()

    def _sort(self):
        # Stable tie-breakers also keep date-only sorting chronological within each day.
        self.records.sort(key=lambda r: (r.attendance_date, r.attendance_time[:8], r.id), reverse=True)
        keys = (lambda r: normalize_search(r.full_name), lambda r: r.public_person_id,
                lambda r: r.attendance_date, lambda r: r.attendance_time[:8], lambda r: r.status)
        self.records.sort(key=keys[self.sort_column], reverse=self.sort_order == Qt.SortOrder.DescendingOrder)

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if 0 <= column < len(self.HEADERS):
            self.sort_column, self.sort_order = column, order
            self.replace(self.records)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.records)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.records) or not 0 <= index.column() < 5:
            return None
        record = self.records[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return (record.full_name, record.public_person_id, attendance_date(record.attendance_date),
                    record.attendance_time[:8], 'حاضر')[index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < 5:
            return self.HEADERS[section]
        return None
