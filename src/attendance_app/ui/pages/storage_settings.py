from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget, QSpinBox, QScrollArea
from attendance_app.domain.errors import AppError
from attendance_app.domain.settings import MIN_CAMERA_INDEX, MAX_CAMERA_INDEX
from importlib.metadata import version
from attendance_app.ui.components.cards import Card
from attendance_app.ui.dialogs.people import confirm, plain_label


class StorageSettingsPage(QWidget):
    restored = Signal()

    def __init__(self, service, parent=None, *, settings_service=None, app_name="سامانه حضور و غیاب"):
        super().__init__(parent)
        self.setObjectName('page_settings')
        self.service = service
        self.settings_service = settings_service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card()
        body = QVBoxLayout(card)
        body.setContentsMargins(24, 24, 24, 24)
        body.setSpacing(24)
        if settings_service is not None:
            body.addWidget(plain_label('دوربین پیش‌فرض', 'heading'))
            body.addWidget(plain_label('این انتخاب برای پنجره‌های جدید ثبت و تشخیص چهره استفاده می‌شود.', 'muted'))
            camera_row = QHBoxLayout()
            camera_row.addWidget(plain_label('شماره دوربین'))
            self.camera_index = QSpinBox()
            self.camera_index.setRange(MIN_CAMERA_INDEX, MAX_CAMERA_INDEX)
            self.camera_index.setAccessibleName('شماره دوربین پیش‌فرض')
            camera_row.addWidget(self.camera_index)
            self.save_camera_button = QPushButton('ذخیره دوربین')
            self.save_camera_button.setProperty('variant', 'primary')
            camera_row.addWidget(self.save_camera_button)
            camera_row.addStretch()
            body.addLayout(camera_row)
            self.camera_feedback = plain_label()
            body.addWidget(self.camera_feedback)
            self.save_camera_button.clicked.connect(self.save_camera)
            self.restored.connect(self.refresh_camera)
            self.refresh_camera()
        body.addWidget(plain_label('پشتیبان‌گیری و بازیابی', 'heading'))
        body.addWidget(plain_label('یک نسخه محلی از اطلاعات نگه دارید یا اطلاعات را از پشتیبان معتبر بازیابی کنید.', 'muted'))
        actions = QHBoxLayout()
        self.backup_button = QPushButton('تهیه نسخه پشتیبان')
        self.backup_button.setProperty('variant', 'primary')
        self.restore_button = QPushButton('بازیابی نسخه پشتیبان')
        actions.addWidget(self.backup_button)
        actions.addWidget(self.restore_button)
        actions.addStretch()
        body.addLayout(actions)
        self.feedback = plain_label()
        body.addWidget(self.feedback)
        body.addStretch()
        body.addWidget(plain_label('درباره برنامه', 'heading'))
        self.about = plain_label(app_name + ' · نسخه \u2066' + version('smart-attendance') + '\u2069\n'
                                 + 'سامانه محلی ثبت حضور با تشخیص چهره و گزارش‌گیری اکسل.', 'muted')
        body.addWidget(self.about)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        layout.addWidget(scroll)
        self.backup_button.clicked.connect(self.backup)
        self.restore_button.clicked.connect(self.restore)

    def refresh_camera(self):
        try:
            self.camera_index.setValue(self.settings_service.camera_index())
            self.camera_feedback.clear()
        except AppError as error:
            self.camera_feedback.setText('خطا: ' + str(error))

    def save_camera(self):
        try:
            self.settings_service.save_camera_index(self.camera_index.value())
        except AppError as error:
            self.camera_feedback.setText('خطا: ' + str(error))
        else:
            self.camera_feedback.setText('دوربین پیش‌فرض ذخیره شد؛ در پنجره جدید اعمال می‌شود.')

    def backup(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره نسخه پشتیبان', 'SmartAttendance-backup.db', 'فایل پشتیبان (*.db)')
        if not path:
            return
        if not path.lower().endswith('.db'):
            path += '.db'
        from pathlib import Path
        overwrite = Path(path).exists()
        if overwrite and not confirm(self, 'جایگزینی پشتیبان', 'فایل انتخاب‌شده وجود دارد. جایگزین شود؟', 'جایگزینی'):
            return
        try:
            self.service.backup(path, overwrite=overwrite)
        except AppError as error:
            self.feedback.setText('خطا: ' + str(error))
        else:
            self.feedback.setText('نسخه پشتیبان ذخیره شد.')

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, 'انتخاب نسخه پشتیبان', '', 'فایل پشتیبان (*.db)')
        if not path:
            return
        if not confirm(self, 'بازیابی اطلاعات', 'اطلاعات فعلی با پشتیبان انتخاب‌شده جایگزین می‌شود. پیش از بازیابی، یک نسخه بازیابی از اطلاعات فعلی نگه‌داری خواهد شد. ادامه می‌دهید؟', 'بازیابی'):
            return
        try:
            self.service.restore(path, confirmed=True)
        except AppError as error:
            self.feedback.setText('خطا: ' + str(error))
        else:
            self.restored.emit()
            self.feedback.setText('اطلاعات بازیابی شد. نسخه قبلی در پوشه پشتیبان‌های برنامه محفوظ است.')
