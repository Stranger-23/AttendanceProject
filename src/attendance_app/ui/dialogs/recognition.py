"""Recognition preview; Qt paints Persian labels without altering camera orientation."""
import cv2
from datetime import datetime
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSpinBox, QLabel
from attendance_app.recognition.worker import RecognitionWorker
from attendance_app.domain.settings import MIN_CAMERA_INDEX, MAX_CAMERA_INDEX
from attendance_app.ui.dialogs.people import plain_label
from attendance_app.ui.formatting import attendance_date


class RecognitionDialog(QDialog):
    def __init__(self, model_dir, templates, parent=None, *, worker_factory=RecognitionWorker, attendance_service=None, camera_index=0):
        super().__init__(parent)
        self.model_dir, self.templates = model_dir, templates
        self.worker_factory = worker_factory
        self.attendance_service = attendance_service
        self.worker = None
        self.pending_result = None
        self.results = []
        self.setWindowTitle('تشخیص چهره')
        self.resize(760, 640)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(plain_label('تشخیص چهره', 'heading'))
        guidance = ('حضور هر فرد پس از شناسایی پایدار، یک بار در روز ثبت می‌شود.' if attendance_service is not None
                    else 'نام افراد شناسایی‌شده نمایش داده می‌شود. حضور و غیاب ثبت نمی‌شود.')
        layout.addWidget(plain_label(guidance, 'muted'))
        self.current_datetime = plain_label('', 'muted')
        self.current_datetime.setObjectName('recognition_current_datetime')
        self.current_datetime.setAccessibleName('تاریخ و ساعت فعلی')
        layout.addWidget(self.current_datetime)
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.update_clock()
        row = QHBoxLayout()
        row.addWidget(plain_label('شماره دوربین'))
        self.camera_index = QSpinBox()
        self.camera_index.setRange(MIN_CAMERA_INDEX, MAX_CAMERA_INDEX)
        self.camera_index.setValue(camera_index)
        self.camera_index.setAccessibleName('شماره دوربین')
        row.addWidget(self.camera_index)
        self.start_button = QPushButton('شروع دوربین')
        self.stop_button = QPushButton('توقف دوربین')
        self.stop_button.setEnabled(False)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        layout.addLayout(row)
        self.preview = QLabel('دوربین خاموش است')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(320, 180)
        self.preview.setProperty('role', 'cameraPreview')
        layout.addWidget(self.preview, 1)
        self.status = plain_label('برای آغاز، دوربین را روشن کنید.')
        layout.addWidget(self.status)
        self.attendance_feedback = plain_label()
        self.attendance_feedback.setObjectName('attendance_feedback')
        layout.addWidget(self.attendance_feedback)
        close = QPushButton('بستن')
        layout.addWidget(close)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_preview)
        self.start_button.clicked.connect(self.start_camera)
        self.stop_button.clicked.connect(self.stop_camera)
        close.clicked.connect(self.reject)

    def update_clock(self):
        # Presentation only; the recognition worker captures attendance timestamps.
        now = datetime.now().astimezone()
        self.current_datetime.setText('تاریخ: \u2066' + attendance_date(now.date().isoformat())
                                      + '\u2069    ساعت: \u2066' + now.strftime('%H:%M:%S') + '\u2069')

    def showEvent(self, event):
        self.update_clock()
        self.clock_timer.start()
        super().showEvent(event)

    def start_camera(self):
        if self.worker is not None:
            return
        self.results = []
        self.attendance_feedback.clear()
        options = {'attendance_service': self.attendance_service} if self.attendance_service is not None else {}
        self.worker = self.worker_factory(self.model_dir, self.templates, self.camera_index.value(), self, **options)
        self.worker.attendance_status.connect(self.show_attendance_status)
        self.worker.failed.connect(self.camera_error)
        self.worker.finished.connect(self.camera_finished)
        self.start_button.setEnabled(False)
        self.camera_index.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText('در حال آماده‌سازی دوربین و اطلاعات چهره…')
        self.timer.start()
        self.worker.start()

    def show_attendance_status(self, message):
        previous = self.attendance_feedback.text().split('\n') if self.attendance_feedback.text() else []
        # Keep several simultaneous-person outcomes visible without an unbounded history.
        self.attendance_feedback.setText('\n'.join((previous + [message])[-3:]))

    def camera_error(self, message):
        self.timer.stop()
        self.results = []
        self.preview.clear()
        self.status.setText(message)

    def stop_camera(self):
        if self.worker:
            self.timer.stop()
            self.results = []
            self.preview.clear()
            self.worker.requestInterruption()
            self.stop_button.setEnabled(False)
            self.status.setText('در حال بستن دوربین…')

    def camera_finished(self):
        self.timer.stop()
        thread, self.worker = self.worker, None
        if thread:
            thread.deleteLater()
        self.results = []
        self.preview.setText('دوربین خاموش است')
        self.start_button.setEnabled(True)
        self.camera_index.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self.pending_result is not None:
            result, self.pending_result = self.pending_result, None
            self.done(result)

    def update_preview(self):
        packet = self.worker.take_latest() if self.worker else None
        if packet is None:
            return
        frame, self.results = packet
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image)
        painter = QPainter(pixmap)
        painter.setFont(self.font())
        names = []
        for result in self.results:
            x, y, w, h = result.bbox
            name = result.person_name if result.state == 'known' else 'ناشناس'
            names.append(name)
            color = QColor('#16834a' if result.state == 'known' else '#b54708')
            painter.setPen(QPen(color, 2))
            painter.drawRect(QRectF(x, y, w, h))
            label = QRectF(max(0, x), max(0, y-30), max(w, 180), 30)
            painter.fillRect(label, QColor('#ffffff'))
            painter.drawText(label, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)
        painter.end()
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(' · '.join(names) if names else 'چهره‌ای دیده نشد؛ منتظر چهره…')

    def done(self, result):
        if self.worker is not None:
            self.pending_result = result
            self.stop_camera()
            return
        self.clock_timer.stop()
        super().done(result)

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
