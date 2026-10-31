from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from attendance_app.ui.dialogs.people import plain_label
from attendance_app.domain.errors import AppError
from attendance_app.ui.dialogs.recognition import RecognitionDialog


class RecognitionPage(QWidget):
    def __init__(self, model_dir, templates, attendance_service=None, *, settings_service=None):
        super().__init__()
        self.setObjectName('page_attendance')
        self.model_dir, self.templates = model_dir, templates
        self.attendance_service = attendance_service
        self.settings_service = settings_service
        layout = QVBoxLayout(self)
        layout.addWidget(plain_label('تشخیص چهره', 'heading'))
        layout.addWidget(plain_label('پس از شناسایی پایدار چهره، حضور هر فرد یک بار در روز ثبت می‌شود.', 'muted'))
        self.start_button = QPushButton('باز کردن دوربین تشخیص چهره')
        self.start_button.setProperty('variant', 'primary')
        self.start_button.clicked.connect(self.open_camera)
        layout.addWidget(self.start_button)
        self.feedback = plain_label()
        layout.addWidget(self.feedback)
        layout.addStretch()

    def open_camera(self):
        try:
            index = self.settings_service.camera_index() if self.settings_service else 0
            self.feedback.clear()
            RecognitionDialog(self.model_dir, self.templates, self,
                              attendance_service=self.attendance_service, camera_index=index).exec()
        except AppError as error:
            self.feedback.setText('خطا: ' + str(error))
