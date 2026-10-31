from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QGridLayout, QHeaderView, QHBoxLayout, QPushButton,
    QScrollArea, QStackedWidget, QTableView, QVBoxLayout, QWidget,
)
from attendance_app.ui.components.attendance_table import HistoryDelegate
from attendance_app.ui.components.cards import Card
from attendance_app.ui.dialogs.people import plain_label
from attendance_app.ui.formatting import attendance_date
from attendance_app.ui.presenters.dashboard import DashboardPresenter, local_day
from attendance_app.ui.table_models.attendance import AttendanceTableModel


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, service, parent=None, *, day_clock=local_day):
        super().__init__(parent)
        self.setObjectName('page_dashboard')
        self.presenter = DashboardPresenter(service, self, day_clock=day_clock)
        self.snapshot = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName('dashboard_content')
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)
        header = QHBoxLayout()
        self.date_label = plain_label('امروز: —', 'heading')
        self.date_label.setObjectName('dashboard_date')
        header.addWidget(self.date_label, 1)
        self.refresh_button = QPushButton('تازه‌سازی')
        self.refresh_button.setAccessibleName('تازه‌سازی داشبورد و تلاش دوباره')
        self.refresh_button.setProperty('variant', 'primary')
        header.addWidget(self.refresh_button)
        body.addLayout(header)
        self.feedback = plain_label('', 'error')
        self.feedback.setObjectName('dashboard_feedback')
        self.feedback.hide()
        body.addWidget(self.feedback)
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        self.cards, self.values = [], {}
        for key, title, subtitle in (
            ('registered_people', 'کل افراد ثبت‌شده', 'شامل افراد بایگانی‌شده'),
            ('active_people', 'افراد فعال', 'وضعیت فعلی؛ مستقل از ثبت چهره'),
            ('today_attendance', 'حضورهای ثبت‌شده امروز', 'شامل حضور افراد بایگانی‌شده'),
            ('total_attendance', 'کل حضورهای ثبت‌شده', 'هر فرد در هر روز، یک حضور؛ شامل بایگانی‌شده‌ها'),
        ):
            card = Card()
            column = QVBoxLayout(card)
            column.setContentsMargins(20, 20, 20, 20)
            column.setSpacing(8)
            title_label = plain_label(title)
            title_label.setFixedHeight(44)
            column.addWidget(title_label)
            value = plain_label('—', 'statValue')
            value.setObjectName('dashboard_' + key)
            value.setAccessibleName(title)
            value.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            value.setFixedHeight(48)
            column.addWidget(value)
            column.addWidget(plain_label(subtitle, 'muted'))
            self.cards.append(card)
            self.values[key] = value
        body.addLayout(self.grid)
        self.card_columns = 0
        self._reflow()
        quick = QHBoxLayout()
        self.quick_buttons = {}
        for key, title in (('attendance', 'حضور و غیاب'), ('people', 'مدیریت افراد'), ('history', 'مشاهده تاریخچه')):
            button = QPushButton(title)
            button.setAccessibleName(title)
            button.clicked.connect(lambda checked=False, target=key: self.navigate_requested.emit(target))
            self.quick_buttons[key] = button
            quick.addWidget(button)
        body.addLayout(quick)
        recent = Card()
        recent_body = QVBoxLayout(recent)
        recent_body.setContentsMargins(24, 24, 24, 24)
        recent_body.setSpacing(12)
        recent_header = QHBoxLayout()
        recent_header.addWidget(plain_label('آخرین حضورهای ثبت‌شده', 'heading'), 1)
        recent_header.addWidget(plain_label('۱۰ رکورد اخیر', 'muted'))
        recent_body.addLayout(recent_header)
        self.model = AttendanceTableModel(self)
        # Short dashboard headings; the shared History model and its own headings are unchanged.
        self.model.HEADERS = ('نام', 'شناسه', 'تاریخ', 'ساعت', 'وضعیت')
        self.table = QTableView()
        self.table.setObjectName('dashboard_recent')
        self.table.setAccessibleName('ده حضور اخیر')
        self.table.setModel(self.model)
        self.table.setItemDelegate(HistoryDelegate(self.table))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(100)
        for column, width in ((1, 120), (2, 130), (3, 112), (4, 100)):
            self.table.setColumnWidth(column, width)
        self.table.setMinimumHeight(240)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.state = plain_label('در حال دریافت اطلاعات داشبورد…', 'muted')
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.state)
        self.stack.setCurrentIndex(1)
        self.stack.setMinimumHeight(240)
        recent_body.addWidget(self.stack)
        self.history_button = QPushButton('مشاهده تاریخچه')
        self.history_button.clicked.connect(lambda: self.navigate_requested.emit('history'))
        recent_body.addWidget(self.history_button)
        body.addWidget(recent)
        body.addStretch()
        self.scroll.setWidget(content)
        layout.addWidget(self.scroll)
        self.refresh_button.clicked.connect(self.refresh)
        self.presenter.loading.connect(self.show_loading)
        self.presenter.loaded.connect(self.show_snapshot)
        self.presenter.failed.connect(self.show_error)
        self.day_timer = QTimer(self)
        self.day_timer.setInterval(60_000)
        self.day_timer.timeout.connect(self.check_day)

    def _reflow(self):
        columns = 4 if self.width() >= 900 else 2
        if columns == self.card_columns:
            return
        self.card_columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for column in range(4):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.presenter.closing:
            self.day_timer.start()

    def hideEvent(self, event):
        self.day_timer.stop()
        super().hideEvent(event)

    def check_day(self):
        if self.isVisible() and self.presenter.requested_day != self.presenter.day_clock():
            self.refresh()

    def refresh(self, *_):
        self.presenter.request()

    def show_loading(self, day):
        self.snapshot = None
        self.feedback.hide()
        self.date_label.setText('امروز: \u2066' + attendance_date(day) + '\u2069')
        for value in self.values.values():
            value.setText('—')
        self.model.replace([])
        self.state.setText('در حال دریافت اطلاعات داشبورد…')
        self.stack.setCurrentIndex(1)

    def show_snapshot(self, snapshot):
        self.snapshot = snapshot
        self.feedback.hide()
        self.date_label.setText('امروز: \u2066' + attendance_date(snapshot.captured_day) + '\u2069')
        for key, value in self.values.items():
            value.setText(str(getattr(snapshot, key)))
        self.model.replace(snapshot.recent)
        self.state.setText('هنوز حضوری ثبت نشده است.')
        self.stack.setCurrentIndex(0 if snapshot.recent else 1)

    def show_error(self, message):
        self.snapshot = None
        for value in self.values.values():
            value.setText('—')
        self.model.replace([])
        self.feedback.setText(message)
        self.feedback.show()
        self.state.setText('دریافت اطلاعات ممکن نشد. «تازه‌سازی» را برای تلاش دوباره انتخاب کنید.')
        self.stack.setCurrentIndex(1)

    def shutdown(self):
        self.day_timer.stop()
        return self.presenter.shutdown()
