from PySide6.QtCore import QDate, QLocale, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QHeaderView, QHBoxLayout, QLineEdit,
    QPushButton, QStackedWidget, QTableView, QVBoxLayout, QWidget,
)
from attendance_app.ui.components.cards import Card
from attendance_app.ui.components.icons import icon
from attendance_app.ui.dialogs.people import plain_label
from attendance_app.ui.dialogs.attendance import AttendanceDetailsDialog
from attendance_app.ui.formatting import PERSIAN_CALENDAR, canonical_date
from attendance_app.ui.presenters.history import HistoryPresenter
from attendance_app.ui.table_models.attendance import AttendanceTableModel
from attendance_app.ui.components.attendance_table import HistoryDelegate


def date_picker(name):
    picker = QDateEdit()
    picker.setAccessibleName(name)
    # QDate stays an absolute day; only editing/formatting uses the Persian calendar.
    picker.setCalendar(PERSIAN_CALENDAR)
    # Keep the requested numeric YYYY/MM/DD representation, with no localized month names.
    picker.setLocale(QLocale.c())
    picker.setDateRange(QDate(622, 3, 22), QDate(9999, 12, 31))
    picker.setDate(QDate.currentDate())
    picker.setKeyboardTracking(False)
    picker.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    # Changing direction rewrites Qt's section order; apply the exact format last.
    picker.setDisplayFormat('yyyy/MM/dd')
    # Numeric sections avoid month names even in the date-selection control.
    picker.setCalendarPopup(False)
    picker.setMinimumWidth(132)
    return picker


class HistoryPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName('page_history')
        self.presenter = HistoryPresenter(service, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card()
        body = QVBoxLayout(card)
        body.setContentsMargins(24, 24, 24, 24)
        body.setSpacing(12)
        body.addWidget(plain_label('سوابق حضور ثبت‌شده · تاریخ‌ها به تقویم هجری شمسی', 'muted'))
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName('history_search')
        self.search.setAccessibleName('جست‌وجوی سوابق')
        self.search.setPlaceholderText('نام، نام خانوادگی یا شناسه')
        self.search.addAction(icon('search'), QLineEdit.ActionPosition.LeadingPosition)
        self.person = QComboBox()
        self.person.setAccessibleName('فرد')
        self.person.setMinimumWidth(160)
        self.person.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.person.addItem('همه افراد', None)
        self._field(top, 'جست‌وجو', self.search, 1)
        self._field(top, 'فرد', self.person, 1)
        body.addLayout(top)
        dates = QHBoxLayout()
        self.date_mode = QComboBox()
        self.date_mode.setAccessibleName('محدوده تاریخ')
        self.date_mode.addItems(['همه تاریخها', 'یک روز', 'بازه تاریخ'])
        self.start_date = date_picker('تاریخ آغاز یا روز حضور')
        self.end_date = date_picker('تاریخ پایان')
        self._field(dates, 'محدوده تاریخ', self.date_mode)
        self._field(dates, 'روز / از تاریخ', self.start_date)
        self._field(dates, 'تا تاریخ', self.end_date)
        dates.addStretch()
        body.addLayout(dates)
        actions = QHBoxLayout()
        self.refresh_button = QPushButton('تازه‌سازی')
        self.refresh_button.setProperty('variant', 'primary')
        self.reset_button = QPushButton('پاک کردن فیلترها')
        self.details_button = QPushButton('جزئیات')
        for button in (self.refresh_button, self.reset_button, self.details_button):
            actions.addWidget(button)
        actions.addStretch()
        body.addLayout(actions)
        self.feedback = plain_label('', 'error')
        self.feedback.setObjectName('history_feedback')
        self.feedback.hide()
        body.addWidget(self.feedback)
        self.model = AttendanceTableModel(self)
        self.table = QTableView()
        self.table.setObjectName('history_table')
        self.table.setAccessibleName('سوابق حضور')
        self.table.setModel(self.model)
        self.table.setItemDelegate(HistoryDelegate(self.table))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(52)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(100)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in ((1, 120), (2, 130), (3, 112), (4, 112)):
            self.table.setColumnWidth(column, width)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.state = plain_label('', 'muted')
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.state)
        body.addWidget(self.stack, 1)
        layout.addWidget(card)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(self.search_changed)
        self.person.currentIndexChanged.connect(self.refresh)
        self.date_mode.currentIndexChanged.connect(self.refresh)
        self.start_date.dateChanged.connect(self.refresh)
        self.end_date.dateChanged.connect(self.refresh)
        self.refresh_button.clicked.connect(self.refresh)
        self.reset_button.clicked.connect(self.reset_filters)
        self.details_button.clicked.connect(self.open_details)
        self.table.doubleClicked.connect(self.open_details)
        self.table.selectionModel().selectionChanged.connect(self.update_actions)
        self.presenter.loaded.connect(self.show_records)
        self.presenter.failed.connect(self.show_error)
        self._date_enabled()
        self.update_actions()

    @staticmethod
    def _field(row, title, control, stretch=0):
        column = QVBoxLayout()
        column.addWidget(plain_label(title))
        column.addWidget(control)
        row.addLayout(column, stretch)

    def _date_enabled(self):
        self.start_date.setEnabled(self.date_mode.currentIndex() != 0)
        self.end_date.setEnabled(self.date_mode.currentIndex() == 2)

    def search_changed(self):
        self.presenter.invalidate()
        self.show_state('در حال دریافت سوابق…')
        self.timer.start()

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
        self.show_state('در حال دریافت سوابق…')
        self.presenter.request(dict(query=self.search.text(), person_id=self.person.currentData(),
                                    start_date=start, end_date=end))

    def show_state(self, text):
        self.model.replace([])
        self.state.setText(text)
        self.stack.setCurrentIndex(1)
        self.update_actions()

    def show_error(self, message):
        self.show_state('دریافت سوابق ممکن نشد. «تازه‌سازی» را انتخاب کنید.')
        self.feedback.setText(message)
        self.feedback.show()

    def show_records(self, records, people):
        selected = self.person.currentData()
        self.person.blockSignals(True)
        self.person.clear()
        self.person.addItem('همه افراد', None)
        for person in people:
            suffix = ' · بایگانی‌شده' if not person.is_active else ''
            self.person.addItem(f'{person.full_name} · {person.public_person_id}{suffix}', person.id)
        index = self.person.findData(selected)
        self.person.setCurrentIndex(max(0, index))
        self.person.blockSignals(False)
        # A restore may remove the selected person: refresh using the visible selection.
        if selected is not None and index < 0:
            self.refresh()
            return
        self.feedback.hide()
        self.model.replace(records)
        self.stack.setCurrentIndex(0 if records else 1)
        filtered = bool(self.search.text().strip() or selected is not None or self.date_mode.currentIndex())
        self.state.setText('رکوردی با فیلترهای انتخاب‌شده یافت نشد.' if filtered else 'هنوز حضوری ثبت نشده است.')
        self.update_actions()

    def reset_filters(self):
        for control in (self.search, self.person, self.date_mode, self.start_date, self.end_date):
            control.blockSignals(True)
        self.search.clear()
        self.person.setCurrentIndex(0)
        self.date_mode.setCurrentIndex(0)
        self.start_date.setDate(QDate.currentDate())
        self.end_date.setDate(QDate.currentDate())
        for control in (self.search, self.person, self.date_mode, self.start_date, self.end_date):
            control.blockSignals(False)
        self.refresh()

    def update_actions(self, *_):
        self.details_button.setEnabled(bool(self.table.selectionModel().selectedRows()) and self.stack.currentIndex() == 0)

    def open_details(self, *_):
        rows = self.table.selectionModel().selectedRows()
        if rows and self.stack.currentIndex() == 0:
            AttendanceDetailsDialog(self.model.records[rows[0].row()], self).exec()

    def shutdown(self):
        self.timer.stop()
        return self.presenter.shutdown()
