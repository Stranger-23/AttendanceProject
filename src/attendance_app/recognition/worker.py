"""Camera and inference stay in QThread; one-slot mailbox prevents UI backlog."""
import cv2
from datetime import datetime
from threading import Event, Lock
from time import monotonic

from PySide6.QtCore import QThread, Signal

from attendance_app.recognition.camera import Camera
from attendance_app.recognition.engine import FaceEngine, RecognitionError


class CameraWorker(QThread):
    sample_ready = Signal(object)
    sample_rejected = Signal(str)
    failed = Signal(str)

    def __init__(self, model_dir, config, camera_index=0, parent=None, *, engine_factory=FaceEngine, camera_factory=Camera):
        super().__init__(parent)
        self.model_dir, self.config, self.camera_index = model_dir, config, camera_index
        self.engine_factory, self.camera_factory = engine_factory, camera_factory
        self._capture_request = Event()
        self._lock = Lock()
        self._latest = None
        self._last_sample = float('-inf')

    def request_sample(self):
        self._capture_request.set()

    def take_latest(self):
        with self._lock:
            packet, self._latest = self._latest, None
            return packet

    def run(self):
        try:
            engine = self.engine_factory(self.model_dir, self.config)
            with self.camera_factory(self.camera_index) as camera:
                while not self.isInterruptionRequested():
                    frame = camera.read()
                    requested = self._capture_request.is_set()
                    if requested:
                        self._capture_request.clear()
                    result = engine.analyze(frame, extract=requested)
                    if requested:
                        if result.embedding is None:
                            self.sample_rejected.emit(result.message)
                        elif monotonic() - self._last_sample < self.config.sample_interval_seconds:
                            self.sample_rejected.emit('کمی مکث کنید و زاویه چهره را اندکی تغییر دهید.')
                        else:
                            self._last_sample = monotonic()
                            self.sample_ready.emit(result.embedding.copy())
                    with self._lock:
                        self._latest = (frame, result)
        except RecognitionError as error:
            self.failed.emit(str(error))
        except Exception as error:
            # Avoid exception text containing frames/embeddings or person data.
            self.failed.emit('خطای غیرمنتظره در دوربین یا مدل: ' + type(error).__name__)
        finally:
            self._capture_request.clear()
            with self._lock:
                self._latest = None


class RecognitionWorker(QThread):
    failed = Signal(str)
    attendance_status = Signal(str)

    def __init__(self, model_dir, templates, camera_index=0, parent=None, *,
                 config=None, engine_factory=FaceEngine, camera_factory=Camera, attendance_service=None):
        super().__init__(parent)
        self.model_dir, self.templates, self.camera_index = model_dir, templates, camera_index
        self.config = config
        self.attendance_service = attendance_service
        self.engine_factory, self.camera_factory = engine_factory, camera_factory
        self._lock, self._latest = Lock(), None

    def take_latest(self):
        with self._lock:
            packet, self._latest = self._latest, None
            return packet

    def run(self):
        import logging
        from attendance_app.domain.errors import AppError
        from attendance_app.recognition.matching import RecognitionEngine
        logger = logging.getLogger('attendance_app.recognition')
        recorder = None
        try:
            stage = "gallery initialization"
            matcher = RecognitionEngine(self.templates.list_active(), self.config)
            stage = "model initialization"
            engine = self.engine_factory(self.model_dir)
            if self.attendance_service is not None:
                from attendance_app.application.attendance_recorder import AttendanceRecorder
                recorder = AttendanceRecorder(self.attendance_service, self.attendance_status.emit)
            stage = "camera open"
            with self.camera_factory(self.camera_index) as camera:
                while not self.isInterruptionRequested():
                    stage = "camera frame read"
                    frame = camera.read()
                    observed_at = datetime.now().astimezone()
                    stage = "face recognition"
                    results = matcher.recognize(engine.analyze_all(frame))
                    if recorder is not None:
                        recorder.submit(results, observed_at)
                    with self._lock:
                        self._latest = (frame, results)
        except AppError as error:
            logger.error('Recognition stopped during %s: %s', stage, type(error).__name__)
            message = str(error) if not isinstance(error.__cause__, cv2.error) else 'آماده‌سازی یا پردازش مدل چهره ممکن نشد. گزارش برنامه را بررسی کنید.'
            self.failed.emit(message)
        except Exception as error:
            logger.error('Recognition failed during %s: %s', stage, type(error).__name__)
            self.failed.emit('خطا در راه‌اندازی تشخیص چهره یا دریافت تصویر؛ گزارش برنامه را بررسی کنید.')
        finally:
            if recorder is not None:
                recorder.close()
            with self._lock:
                self._latest = None
