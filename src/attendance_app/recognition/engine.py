"""Offline YuNet/SFace adapter. Instances belong to their creating worker."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from attendance_app.configuration.settings import EnrollmentConfig
from attendance_app.domain.errors import AppError

MODELS = (
    ('face_detection_yunet_2026may.onnx', 229738, 'ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0'),
    ('face_recognition_sface_2021dec.onnx', 38696353, '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'),
)
MODEL_ID = 'sface-2021dec:' + MODELS[1][2]
ALIGNMENT_ID = 'yunet-2026may:' + MODELS[0][2]


class RecognitionError(AppError):
    pass


def verify_models(directory):
    paths = []
    for name, size, digest in MODELS:
        path = Path(directory) / name
        try:
            actual = sha256(path.read_bytes()).hexdigest()
            if path.stat().st_size != size or actual != digest:
                raise RecognitionError('فایل مدل معتبر نیست: ' + name)
        except OSError as error:
            raise RecognitionError('خواندن فایل مدل ممکن نشد: ' + name) from error
        paths.append(path)
    return paths


@dataclass
class Analysis:
    faces: np.ndarray
    status: str
    message: str
    detection_ms: float
    embedding_ms: float = 0.0
    embedding: np.ndarray | None = None
    blur: float | None = None
    brightness: float | None = None


class FaceEngine:
    def __init__(self, model_dir, config=None):
        self.config = config or EnrollmentConfig()
        detector, recognizer = verify_models(model_dir)
        try:
            self.detector = cv2.FaceDetectorYN.create(str(detector), '', (640, 480), self.config.detector_score)
            self.recognizer = cv2.FaceRecognizerSF.create(str(recognizer), '')
        except cv2.error as error:
            raise RecognitionError('خطای بارگذاری مدل OpenCV:\n' + str(error)) from error

    def analyze(self, frame, *, extract=False):
        if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise RecognitionError('قالب تصویر دوربین معتبر نیست.')
        try:
            height, width = frame.shape[:2]
            self.detector.setInputSize((width, height))
            start = perf_counter()
            _, faces = self.detector.detect(frame)
            elapsed = (perf_counter() - start) * 1000
            faces = np.empty((0, 15), np.float32) if faces is None else faces
            return self._analyze_detected(frame, faces, elapsed, extract)
        except cv2.error as error:
            # Preserve the exact API/input-shape error. Never substitute models/backends.
            raise RecognitionError('خطای پردازش OpenCV:\n' + str(error)) from error

    def _analyze_detected(self, frame, faces, elapsed, extract):
        height, width = frame.shape[:2]
        try:
            if len(faces) == 0:
                return Analysis(faces, 'no_face', 'چهره‌ای دیده نشد؛ روبه‌روی دوربین قرار بگیرید.', elapsed)
            if len(faces) != 1:
                return Analysis(faces, 'multiple_faces', 'بیش از یک چهره دیده شد؛ فقط یک نفر در تصویر باشد.', elapsed)
            face = faces[0]
            if face.shape != (15,) or not np.isfinite(face).all():
                raise RecognitionError('خروجی نقاط چهره معتبر نیست.')
            x, y, w, h = face[:4]
            x0, y0 = max(0, int(x)), max(0, int(y))
            x1, y1 = min(width, int(x + w)), min(height, int(y + h))
            if w < self.config.min_face_pixels or h < self.config.min_face_pixels or x < 0 or y < 0 or x+w > width or y+h > height or x1 <= x0 or y1 <= y0:
                return Analysis(faces, 'small_face', 'چهره را کامل و کمی نزدیک‌تر به دوربین قرار دهید.', elapsed)
            gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            brightness = float(gray.mean())
            result = Analysis(faces, 'ready', 'تصویر مناسب است؛ یک نمونه ثبت کنید.', elapsed, blur=blur, brightness=brightness)
            if not self.config.min_brightness <= brightness <= self.config.max_brightness:
                result.status, result.message = 'lighting', 'نور چهره مناسب نیست؛ نور محیط را تنظیم کنید.'
            elif blur < self.config.min_blur_variance:
                result.status, result.message = 'blurred', 'تصویر تار است؛ ثابت بمانید و وضوح دوربین را بررسی کنید.'
            elif extract:
                before = perf_counter()
                aligned = self.recognizer.alignCrop(frame, face)
                feature = np.asarray(self.recognizer.feature(aligned), dtype=np.float32).reshape(-1)
                if feature.shape != (128,) or not np.isfinite(feature).all() or np.linalg.norm(feature) <= 0:
                    raise RecognitionError('بردار چهره معتبر نیست.')
                result.embedding = feature / np.linalg.norm(feature)
                result.embedding_ms = (perf_counter() - before) * 1000
            return result
        except cv2.error as error:
            raise RecognitionError('پردازش چهره ممکن نشد.') from error

    def analyze_all(self, frame):
        """Detect once, then apply the enrollment quality/embedding path per face."""
        if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise RecognitionError('قالب تصویر دوربین معتبر نیست.')
        try:
            height, width = frame.shape[:2]
            self.detector.setInputSize((width, height))
            _, faces = self.detector.detect(frame)
            if faces is None:
                return []
            return [self._analyze_detected(frame, np.asarray([face]), 0, True) for face in faces]
        except cv2.error as error:
            raise RecognitionError('پردازش چهره ممکن نشد.') from error

    def similarity(self, first, second):
        a, b = np.asarray(first, np.float32).reshape(-1), np.asarray(second, np.float32).reshape(-1)
        if a.shape != (128,) or b.shape != (128,) or not np.isfinite(a).all() or not np.isfinite(b).all() or min(np.linalg.norm(a), np.linalg.norm(b)) <= 0:
            raise RecognitionError('بردار مقایسه معتبر نیست.')
        return float(self.recognizer.match(a.reshape(1, -1), b.reshape(1, -1), cv2.FaceRecognizerSF_FR_COSINE))
