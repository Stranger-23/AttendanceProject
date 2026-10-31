"""Bounded report reads and one independent export, with main-thread callbacks."""
import logging

from PySide6.QtCore import QThread, Signal

from attendance_app.domain.errors import AppError
from attendance_app.ui.presenters.history import HistoryPresenter


class ReportRead(QThread):
    def __init__(self, service, filters, parent):
        super().__init__(parent)
        self.service, self.filters = service, filters
        self.result = self.error = None

    def run(self):
        try:
            self.result = self.service.read(self.filters)
        except AppError as error:
            self.error = str(error)
        except Exception as error:
            logging.getLogger('attendance_app.reports').error('Report read failed: %s', type(error).__name__)
            self.error = 'دریافت گزارش ممکن نشد؛ دوباره تلاش کنید.'


class ExportWrite(QThread):
    def __init__(self, service, snapshot, path, overwrite, parent):
        super().__init__(parent)
        self.service, self.snapshot, self.path, self.overwrite = service, snapshot, path, overwrite
        self.error = None

    def run(self):
        try:
            self.service.export(self.snapshot, self.path, overwrite=self.overwrite)
        except AppError as error:
            self.error = str(error)
        except Exception as error:
            logging.getLogger('attendance_app.reports').error('Export failed: %s', type(error).__name__)
            self.error = 'ذخیره اکسل ممکن نشد؛ دوباره تلاش کنید.'


class ReportsPresenter(HistoryPresenter):
    exported = Signal(str)
    export_failed = Signal(str)
    export_idle = Signal()

    def __init__(self, service, export_service, parent=None):
        super().__init__(service, parent)
        self.export_service = export_service
        self.export_worker = None

    def request(self, filters):
        if self.closing:
            return
        self.invalidate()
        self.pending = (self.generation, filters)
        if self.worker is None:
            self._start()

    def _start(self):
        generation, filters = self.pending
        self.pending = None
        self.worker = ReportRead(self.service, filters, self)
        self.worker.finished.connect(lambda: self._finished(generation))
        self.worker.start()

    def export(self, snapshot, path, overwrite=False):
        if self.closing or self.export_worker is not None:
            return False
        self.export_worker = ExportWrite(self.export_service, snapshot, path, overwrite, self)
        self.export_worker.finished.connect(self._export_finished)
        self.export_worker.start()
        return True

    def _export_finished(self):
        worker, self.export_worker = self.export_worker, None
        if not self.closing:
            if worker.error:
                self.export_failed.emit(worker.error)
            else:
                self.exported.emit(str(worker.path))
        worker.deleteLater()
        self.export_idle.emit()
        if self.worker is None:
            self.idle.emit()

    def shutdown(self):
        return super().shutdown() and self.export_worker is None
