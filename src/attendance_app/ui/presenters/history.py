"""One thread-owned read at a time; only the newest requested filters may publish."""
import logging

from PySide6.QtCore import QObject, QThread, Signal
from attendance_app.domain.errors import AppError


class HistoryRead(QThread):
    def __init__(self, service, filters, parent):
        super().__init__(parent)
        self.service, self.filters = service, filters
        self.result, self.error = None, None

    def run(self):
        try:
            self.result = (self.service.search_history(**self.filters), self.service.list_history_people())
        except AppError as error:
            self.error = str(error)
        except Exception as error:
            logging.getLogger('attendance_app.history').error('History read failed: %s', type(error).__name__)
            self.error = 'دریافت سوابق حضور ممکن نشد. دوباره تلاش کنید.'


class HistoryPresenter(QObject):
    loaded = Signal(object, object)
    failed = Signal(str)
    idle = Signal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.worker = None
        self.pending = None
        self.generation = 0
        self.closing = False

    def invalidate(self):
        self.generation += 1
        self.pending = None

    def request(self, filters):
        if self.closing:
            return
        self.invalidate()
        self.pending = (self.generation, dict(filters))
        if self.worker is None:
            self._start()

    def _start(self):
        generation, filters = self.pending
        self.pending = None
        self.worker = HistoryRead(self.service, filters, self)
        self.worker.finished.connect(lambda: self._finished(generation))
        self.worker.start()

    def _finished(self, generation):
        worker, self.worker = self.worker, None
        if not self.closing and generation == self.generation:
            if worker.error is not None:
                self.failed.emit(worker.error)
            else:
                self.loaded.emit(*worker.result)
        worker.deleteLater()
        if self.pending is not None and not self.closing:
            self._start()
        elif self.worker is None:
            self.idle.emit()

    def shutdown(self):
        self.closing = True
        self.invalidate()
        return self.worker is None
