from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from attendance_app.ui.formatting import registration_date


class PeopleTableModel(QAbstractTableModel):
    HEADERS = ('نام و نام خانوادگی', 'شناسه', 'تاریخ ثبت (میلادی)', 'وضعیت')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.people = []

    def replace(self, people):
        self.beginResetModel()
        self.people = list(people)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.people)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.people):
            return None
        person = self.people[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return (person.full_name, person.person_id, "\u2066" + registration_date(person.created_at) + "\u2069",
                    'فعال' if person.is_active else 'بایگانی‌شده')[index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
