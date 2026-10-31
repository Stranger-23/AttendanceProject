"""Reports share History controls and table behavior without changing History."""
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QPushButton, QScrollArea

from attendance_app.domain.reports import ReportFilters
from attendance_app.ui.dialogs.people import confirm, plain_label
from attendance_app.ui.formatting import canonical_date
from attendance_app.ui.pages.history import HistoryPage
from attendance_app.ui.presenters.reports import ReportsPresenter


class ReportsPage(HistoryPage):
    def __init__(self, service, export_service, parent=None):
        self.snapshot = None
        super().__init__(service, parent)
        self.setObjectName('page_reports')
        self.search.setObjectName('reports_search')
        self.search.setAccessibleName('جست‌وجوی گزارش حضور')
        self.table.setObjectName('reports_table')
        self.table.setAccessibleName('پیش‌نمایش گزارش حضور')
        self.feedback.setObjectName('reports_feedback')
        self.presenter.deleteLater()
        self.presenter = ReportsPresenter(service, export_service, self)
        self.presenter.loaded.connect(self.show_records)
        self.presenter.failed.connect(self.show_error)
        self.presenter.exported.connect(self.export_success)
        self.presenter.export_failed.connect(self.export_error)
        self.presenter.export_idle.connect(self.update_actions)
        card = self.layout().takeAt(0).widget()
        body = card.layout()
        body.itemAt(0).widget().setText('گزارش حضور ثبت‌شده · تاریخ‌ها به تقویم هجری شمسی')
        self.details_button.hide()
        self.table.doubleClicked.disconnect()
        self.status = QComboBox()
        self.status.setAccessibleName('وضعیت حضور در گزارش')
        self.status.addItem('همه وضعیتها', None)
        self.status.addItem('حاضر', 'present')
        dates_row = body.itemAt(2).layout()
        dates_row.takeAt(dates_row.count() - 1)
        self._field(dates_row, 'وضعیت حضور', self.status)
        dates_row.addStretch()
        self.refresh_button.setProperty('variant', '')
        self.summary = plain_label('حضورهای ثبت‌شده (نفر-روز): —    افراد دارای حضور: —', 'heading')
        body.insertWidget(body.count() - 1, self.summary)
        body.addWidget(plain_label('خروجی اکسل شامل تمام رکوردهای پیش‌نمایش، با همین ترتیب است. برای دریافت تغییرات، تازه‌سازی کنید.', 'muted'))
        self.export_button = QPushButton('خروجی اکسل')
        self.export_button.setProperty('variant', 'primary')
        self.export_button.setAccessibleName('خروجی اکسل گزارش نمایش داده‌شده')
        body.addWidget(self.export_button)
        self.export_feedback = plain_label()
        body.addWidget(self.export_feedback)
        self.table.setMinimumHeight(220)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        self.layout().addWidget(scroll)
        self.status.currentIndexChanged.connect(self.refresh)
        self.export_button.clicked.connect(self.export_report)
        self.update_actions()

    def show_state(self, text):
        self.snapshot = None
        if hasattr(self, 'summary'):
            self.summary.setText('حضورهای ثبت‌شده (نفر-روز): —    افراد دارای حضور: —')
        super().show_state(text)

    def search_changed(self):
        self.presenter.invalidate()
        self.show_state('در حال دریافت گزارش…')
        self.timer.start()

    def show_error(self, message):
        self.show_state('دریافت گزارش ممکن نشد. «تازه‌سازی» را انتخاب کنید.')
        self.feedback.setText(message)
        self.feedback.show()

    def refresh(self, *_):
        self.timer.stop()
        self._date_enabled()
        mode = self.date_mode.currentIndex()
        start = canonical_date(self.start_date.date()) if mode else None
        end = canonical_date(self.end_date.date()) if mode == 2 else start
        self.feedback.hide()
        if start is not None and start > end:
            self.presenter.invalidate()
            self.show_state('محدوده تاریخ را اصلاح کنید.')
            self.feedback.setText('تاریخ آغاز باید پیش از تاریخ پایان یا برابر با آن باشد.')
            self.feedback.show()
            return
        self.show_state('در حال دریافت گزارش…')
        self.presenter.request(ReportFilters(self.search.text(), self.person.currentData(), start, end,
                                             self.status.currentData()))

    def show_records(self, snapshot, people):
        selected = self.person.currentData()
        super().show_records(snapshot.records, people)
        if selected is not None and all(p.id != selected for p in people):
            return
        self.snapshot = snapshot
        self.summary.setText(f'حضورهای ثبت‌شده (نفر-روز): {snapshot.record_count}    افراد دارای حضور: {snapshot.people_count}')
        self.update_actions()

    def reset_filters(self):
        self.status.blockSignals(True)
        self.status.setCurrentIndex(0)
        self.status.blockSignals(False)
        super().reset_filters()

    def update_actions(self, *_):
        super().update_actions()
        if hasattr(self, 'export_button'):
            self.export_button.setEnabled(bool(self.snapshot and self.snapshot.records)
                                          and self.presenter.export_worker is None and not self.presenter.closing)

    def export_report(self):
        if not self.export_button.isEnabled():
            return
        snapshot = replace(self.snapshot, records=tuple(self.model.records))
        generation = self.presenter.generation
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره گزارش اکسل', 'Attendance-report.xlsx',
                                             'فایل اکسل (*.xlsx)', options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        overwrite = Path(path).exists()
        if overwrite and not confirm(self, 'جایگزینی گزارش', 'فایل انتخاب‌شده وجود دارد. جایگزین شود؟', 'جایگزینی'):
            return
        # Modal dialogs process events; restore/read completion must not export an old preview.
        if generation != self.presenter.generation or self.snapshot is None:
            return
        if self.presenter.export(snapshot, path, overwrite):
            self.export_feedback.setText('در حال ذخیره اکسل…')
            self.update_actions()

    def export_success(self, path):
        self.export_feedback.setText('گزارش اکسل ذخیره شد: ' + '\u2066' + path + '\u2069')

    def export_error(self, message):
        self.export_feedback.setText('خطا: ' + message)
