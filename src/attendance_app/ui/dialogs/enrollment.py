"""Persian capture dialog shared by enrollment and isolated technical preview."""
import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from attendance_app.configuration.settings import EnrollmentConfig
from attendance_app.domain.errors import AppError
from attendance_app.recognition.worker import CameraWorker
from attendance_app.domain.settings import MIN_CAMERA_INDEX, MAX_CAMERA_INDEX
from attendance_app.ui.dialogs.people import plain_label, confirm


class FaceCaptureDialog(QDialog):
    def __init__(self, model_dir, service=None, person=None, expected_ids=(), camera_index=0,
                 parent=None, *, worker_factory=CameraWorker):
        super().__init__(parent)
        self.model_dir, self.service, self.person = model_dir, service, person
        self.expected_ids = expected_ids
        self.worker_factory = worker_factory
        self.config = service.config if service else EnrollmentConfig()
        self.samples = []
        self.worker = None
        self.pending_result = None
        self.capture_pending = False
        self.frame_ready = False
        self.saving = False
        self.setObjectName('face_enrollment' if service else 'face_validation')
        self.setWindowTitle('ثبت چهره' if service else 'آزمایش فنی دوربین و چهره')
        self.resize(720, 640)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(plain_label(self.windowTitle(), 'heading'))
        if person:
            layout.addWidget(plain_label(person.full_name + ' · ' + person.person_id))
        layout.addWidget(plain_label('فقط یک نفر روبه‌روی دوربین باشد. نمونه‌ها را با تغییر اندک زاویه چهره ثبت کنید. تصویر خام ذخیره نمی‌شود.', 'muted'))
        camera_row = QHBoxLayout()
        camera_row.addWidget(plain_label('شماره دوربین'))
        self.camera_index = QSpinBox()
        self.camera_index.setAccessibleName('شماره دوربین')
        self.camera_index.setRange(MIN_CAMERA_INDEX, MAX_CAMERA_INDEX)
        self.camera_index.setValue(camera_index)
        camera_row.addWidget(self.camera_index)
        self.start_button = QPushButton('شروع دوربین')
        self.stop_button = QPushButton('توقف دوربین')
        self.stop_button.setEnabled(False)
        camera_row.addWidget(self.start_button)
        camera_row.addWidget(self.stop_button)
        camera_row.addStretch()
        layout.addLayout(camera_row)
        self.preview = QLabel('دوربین خاموش است')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(320, 160)
        self.preview.setProperty('role', 'cameraPreview')
        layout.addWidget(self.preview, 1)
        self.status = plain_label('برای آغاز، دوربین را روشن کنید.')
        self.status.setObjectName('capture_status')
        layout.addWidget(self.status)
        self.progress = plain_label()
        layout.addWidget(self.progress)
        actions = QHBoxLayout()
        self.capture_button = QPushButton('ثبت نمونه')
        self.capture_button.setProperty('variant', 'primary')
        self.capture_button.setEnabled(False)
        self.reset_button = QPushButton('شروع دوباره')
        self.save_button = QPushButton('ذخیره چهره' if service else 'پایان آزمایش')
        self.save_button.setEnabled(False)
        self.cancel_button = QPushButton('انصراف' if service else 'بستن')
        for button in (self.capture_button, self.reset_button, self.save_button, self.cancel_button):
            button.setAutoDefault(False)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_preview)
        self.start_button.clicked.connect(self.start_camera)
        self.stop_button.clicked.connect(self.stop_camera)
        self.capture_button.clicked.connect(self.capture)
        self.reset_button.clicked.connect(self.reset_samples)
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.reject)
        self.update_progress()

    def start_camera(self):
        if self.worker is not None:
            return
        self.worker = self.worker_factory(self.model_dir, self.config, self.camera_index.value(), self)
        self.worker.sample_ready.connect(self.sample_ready)
        self.worker.sample_rejected.connect(self.sample_rejected)
        self.worker.failed.connect(self.camera_error)
        self.worker.finished.connect(self.camera_finished)
        self.camera_index.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText('در حال آماده‌سازی دوربین و مدل‌ها…')
        self.timer.start()
        self.worker.start()

    def stop_camera(self):
        self.capture_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        if self.worker:
            self.worker.requestInterruption()
            self.status.setText('در حال بستن دوربین…')

    def camera_finished(self):
        self.timer.stop()
        thread, self.worker = self.worker, None
        if thread:
            thread.deleteLater()
        self.camera_index.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.capture_button.setEnabled(False)
        self.capture_pending = False
        self.frame_ready = False
        self.preview.clear()
        self.preview.setText('دوربین خاموش است')
        if self.pending_result is not None:
            result, self.pending_result = self.pending_result, None
            self.done(result)

    def camera_error(self, message):
        self.status.setText(message)
        self.capture_button.setEnabled(False)

    def update_preview(self):
        packet = self.worker.take_latest() if self.worker else None
        if packet is None:
            return
        frame, result = packet
        self.frame_ready = result.status == 'ready'
        if not self.capture_pending:
            self.status.setText(result.message)
        # Layout is RTL; camera pixels are deliberately never mirrored.
        display = frame.copy()
        for face in result.faces:
            x, y, w, h = map(int, face[:4])
            cv2.rectangle(display, (x, y), (x+w, y+h), (231, 92, 108), 2)
            for x, y in face[4:14].reshape(5, 2):
                cv2.circle(display, (int(x), int(y)), 2, (231, 92, 108), -1)
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888).copy()
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.capture_button.setEnabled(self.frame_ready and not self.capture_pending and len(self.samples) < self.config.samples_required and self.stop_button.isEnabled())

    def capture(self):
        if self.worker and not self.capture_pending and len(self.samples) < self.config.samples_required:
            self.capture_pending = True
            self.capture_button.setEnabled(False)
            self.status.setText('در حال ثبت نمونه…')
            self.worker.request_sample()

    def sample_rejected(self, message):
        self.capture_pending = False
        self.status.setText(message)

    def sample_ready(self, vector):
        self.capture_pending = False
        if self.pending_result is not None:
            return
        if len(self.samples) < self.config.samples_required:
            self.samples.append(vector.copy())
        self.update_progress()

    def reset_samples(self):
        if self.capture_pending:
            return
        self.samples.clear()
        self.update_progress()

    def update_progress(self):
        self.progress.setText(f'نمونه‌های ثبت‌شده: {len(self.samples)} از {self.config.samples_required}')
        self.save_button.setEnabled(len(self.samples) == self.config.samples_required)

    def save(self):
        if self.saving or self.pending_result is not None or len(self.samples) != self.config.samples_required:
            return
        if self.service:
            replacing = bool(self.expected_ids)
            if replacing and not confirm(self, 'جایگزینی چهره', 'نمونه‌های قبلی چهره با نمونه‌های جدید جایگزین شوند؟', 'جایگزینی'):
                return
            self.saving = True
            self.save_button.setEnabled(False)
            try:
                self.service.save(self.person, self.samples, expected_ids=self.expected_ids, replace_confirmed=replacing)
            except AppError as error:
                self.saving = False
                self.save_button.setEnabled(True)
                self.status.setText(str(error))
                return
        self.accept()

    def done(self, result):
        if self.worker is not None:
            self.pending_result = result
            self.save_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_camera()
            return
        self.samples.clear()
        super().done(result)

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.done(QDialog.DialogCode.Rejected)
        else:
            self.samples.clear()
            super().closeEvent(event)
