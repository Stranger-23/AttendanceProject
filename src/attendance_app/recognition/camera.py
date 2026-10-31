"""Explicit Windows camera lifetime. No frames are written to disk."""
import cv2
from attendance_app.recognition.engine import RecognitionError


class Camera:
    def __init__(self, index=0):
        self.index = index
        self.capture = None

    def __enter__(self):
        try:
            self.capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            if not self.capture.isOpened():
                raise RecognitionError('دوربین باز نشد. اتصال، دسترسی ویندوز و استفاده در برنامه‌های دیگر را بررسی کنید.')
            return self
        except Exception:
            self.close()
            raise

    def read(self):
        ok, frame = self.capture.read()
        if not ok or frame is None or frame.size == 0:
            raise RecognitionError('دریافت تصویر متوقف شد؛ اتصال دوربین را بررسی کنید.')
        return frame

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def __exit__(self, *_):
        self.close()
