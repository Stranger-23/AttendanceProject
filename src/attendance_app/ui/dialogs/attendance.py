from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout
from attendance_app.ui.dialogs.people import plain_label
from attendance_app.ui.formatting import attendance_date


class AttendanceDetailsDialog(QDialog):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.setWindowTitle('جزئیات حضور')
        self.setObjectName('attendance_details')
        self.resize(440, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(plain_label('جزئیات حضور', 'heading'))
        for title, value in (
            ('نام و نام خانوادگی', record.full_name), ('شناسه فرد', record.public_person_id),
            ('تاریخ حضور', attendance_date(record.attendance_date)),
            ('ساعت حضور', record.attendance_time[:8]), ('وضعیت حضور', 'حاضر'),
            ('اختلاف ساعت ثبت‌شده با زمان جهانی', record.attendance_time[8:]),
            ('وضعیت فعلی فرد', 'فعال' if record.is_active else 'بایگانی‌شده'),
        ):
            layout.addWidget(plain_label(title, 'muted'))
            label = plain_label(value)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            if title in ('تاریخ حضور', 'ساعت حضور', 'اختلاف ساعت ثبت‌شده با زمان جهانی'):
                label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                label.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(label)
        close = QPushButton('بستن')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
