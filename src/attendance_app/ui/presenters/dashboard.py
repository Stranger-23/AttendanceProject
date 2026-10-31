"""Bounded asynchronous dashboard reads with day and generation validation."""
from datetime import datetime
import logging

from PySide6.QtCore import QObject, QThread, Signal, Slot
from attendance_app.domain.errors import AppError


def local_day():
    return datetime.now().astimezone().date().isoformat()


class DashboardRead(QThread):
    def __init__(self, service, generation, day, parent):
        super().__init__(parent)
        self.service, self.generation, self.day = service, generation, day
        self.result, self.error = None, None

    def run(self):
        try:
            self.result = self.service.get_dashboard_snapshot(self.day)
        except AppError as error:
            self.error = str(error)
        except Exception as error:
            logging.getLogger('attendance_app.dashboard').error('Dashboard read failed: %s', type(error).__name__)
            self.error = 'دریافت اطلاعات داشبورد ممکن نشد. دوباره تلاش کنید.'


class DashboardPresenter(QObject):
    loading = Signal(str)
    loaded = Signal(object)
    failed = Signal(str)
    idle = Signal()

    def __init__(self, service, parent=None, *, day_clock=local_day):
        super().__init__(parent)
        self.service, self.day_clock = service, day_clock
        self.worker, self.pending = None, None
        self.generation = 0
        self.requested_day = None
        self.closing = False

    def request(self):
        if self.closing:
            return
        # Capture once per request; the same value drives the query and heading.
        self.requested_day = self.day_clock()
        self.generation += 1
        self.pending = (self.generation, self.requested_day)
        self.loading.emit(self.requested_day)
        if self.worker is None:
            self._start()

    def _start(self):
        generation, day = self.pending
        self.pending = None
        self.worker = DashboardRead(self.service, generation, day, self)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    @Slot()
    def _finished(self):
        worker, self.worker = self.worker, None
        if not self.closing and worker.generation == self.generation:
            # Sleep, midnight or a timezone/clock correction can obsolete this day.
            if worker.day != self.day_clock():
                self.request()
            elif worker.error is not None:
                self.failed.emit(worker.error)
            else:
                self.loaded.emit(worker.result)
        worker.deleteLater()
        if self.pending is not None and not self.closing and self.worker is None:
            self._start()
        elif self.worker is None:
            self.idle.emit()

    def shutdown(self):
        self.closing = True
        self.generation += 1
        self.pending = None
        return self.worker is None
