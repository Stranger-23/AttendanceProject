from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHeaderView, QHBoxLayout, QLineEdit,
    QPushButton, QStackedWidget, QTableView, QVBoxLayout, QWidget,
)
from attendance_app.domain.errors import AppError
from attendance_app.ui.components.cards import Card
from attendance_app.ui.components.icons import icon
from attendance_app.ui.dialogs.people import PersonDetailsDialog, PersonFormDialog, confirm, plain_label
from attendance_app.ui.table_models.people import PeopleTableModel
from attendance_app.ui.dialogs.enrollment import FaceCaptureDialog


class PeoplePage(QWidget):
    def __init__(self, service, parent=None, *, enrollment_service=None, model_dir=None, settings_service=None):
        super().__init__(parent)
        self.setObjectName('page_people')
        self.service = service
        self.settings_service = settings_service
        self.enrollment_service, self.model_dir = enrollment_service, model_dir
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card()
        body = QVBoxLayout(card)
        body.setContentsMargins(24, 24, 24, 24)
        body.setSpacing(16)
        body.addWidget(plain_label('اطلاعات افراد را ثبت، جست‌وجو و ویرایش کنید.', 'muted'))
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        search_column = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName('people_search')
        self.search.setAccessibleName('جست‌وجوی افراد')
        self.search.setPlaceholderText('نام، نام خانوادگی یا شناسه')
        self.search.addAction(icon('search'), QLineEdit.ActionPosition.LeadingPosition)
        search_column.addWidget(plain_label('جست‌وجوی افراد'))
        search_column.addWidget(self.search)
        toolbar.addLayout(search_column, 1)
        filter_column = QVBoxLayout()
        filter_column.addWidget(plain_label('نمایش'))
        self.filter = QComboBox()
        self.filter.setAccessibleName('وضعیت افراد')
        self.filter.addItems(['افراد فعال', 'افراد بایگانی‌شده'])
        filter_column.addWidget(self.filter)
        toolbar.addLayout(filter_column)
        body.addLayout(toolbar)
        actions = QHBoxLayout()
        self.add_button = QPushButton('افزودن فرد')
        self.add_button.setProperty('variant', 'primary')
        self.details_button = QPushButton('جزئیات')
        self.edit_button = QPushButton('ویرایش')
        self.archive_button = QPushButton('غیرفعال‌سازی')
        for button in (self.add_button, self.details_button, self.edit_button, self.archive_button):
            actions.addWidget(button)
        actions.addStretch()
        body.addLayout(actions)
        self.enroll_button = QPushButton('ثبت / جایگزینی چهره')
        body.addWidget(self.enroll_button)
        self.feedback = plain_label()
        self.feedback.setObjectName('people_feedback')
        self.feedback.hide()
        body.addWidget(self.feedback)
        self.model = PeopleTableModel(self)
        self.table = QTableView()
        self.table.setObjectName('people_table')
        self.table.setAccessibleName('فهرست افراد')
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(52)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 112)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.empty = plain_label('هنوز فردی ثبت نشده است. برای شروع «افزودن فرد» را انتخاب کنید.', 'muted')
        from PySide6.QtCore import Qt
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty)
        body.addWidget(self.stack, 1)
        layout.addWidget(card)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.timer.start())
        self.filter.currentIndexChanged.connect(self.refresh)
        self.table.selectionModel().selectionChanged.connect(self.update_actions)
        self.table.doubleClicked.connect(self.open_details)
        self.add_button.clicked.connect(self.open_add)
        self.edit_button.clicked.connect(self.open_edit)
        self.details_button.clicked.connect(self.open_details)
        self.archive_button.clicked.connect(self.archive_selected)
        self.enroll_button.clicked.connect(self.open_enrollment)
        self.update_actions()

    def notify(self, message, error=False):
        self.feedback.setText(('خطا: ' if error else '') + message)
        self.feedback.show()

    def selected_id(self):
        rows = self.table.selectionModel().selectedRows()
        return self.model.people[rows[0].row()].id if rows else None

    def update_actions(self, *_):
        selected = self.selected_id() is not None
        self.edit_button.setEnabled(selected)
        self.details_button.setEnabled(selected)
        self.archive_button.setEnabled(selected and self.filter.currentIndex() == 0)
        self.enroll_button.setEnabled(selected and self.filter.currentIndex() == 0 and self.enrollment_service is not None)

    def refresh(self, *_):
        self.timer.stop()
        try:
            people = self.service.search(self.search.text(), active=self.filter.currentIndex() == 0)
        except AppError as error:
            self.model.replace([])
            self.stack.setCurrentIndex(1)
            self.empty.setText('دریافت فهرست ممکن نشد. دوباره این بخش را باز کنید.')
            self.notify(str(error), True)
        else:
            self.model.replace(people)
            self.stack.setCurrentIndex(0 if people else 1)
            self.empty.setText('فردی با این جست‌وجو یافت نشد.' if self.search.text().strip() else
                               ('فرد بایگانی‌شده‌ای وجود ندارد.' if self.filter.currentIndex() else 'هنوز فردی ثبت نشده است. برای شروع «افزودن فرد» را انتخاب کنید.'))
        self.update_actions()

    def open_add(self):
        dialog = PersonFormDialog(self.service, parent=self)
        dialog.saved.connect(self.person_added)
        dialog.exec()

    def person_added(self, _person):
        self.search.clear()
        self.filter.setCurrentIndex(0)
        self.refresh()
        self.notify('اطلاعات فرد ثبت شد.')

    def open_edit(self):
        self.with_selected(lambda person: self.edit_person(person))

    def edit_person(self, person):
        dialog = PersonFormDialog(self.service, person, self)
        dialog.saved.connect(lambda _: (self.refresh(), self.notify('تغییرات ذخیره شد.')))
        dialog.exec()

    def open_details(self, *_):
        self.with_selected(lambda person: PersonDetailsDialog(person, self,
            face_status=self.enrollment_service.status(person.id) if self.enrollment_service else None).exec())

    def open_enrollment(self):
        def enroll(person):
            person, previous = self.enrollment_service.begin(person.id)
            dialog = FaceCaptureDialog(self.model_dir, self.enrollment_service, person, previous, camera_index=self.settings_service.camera_index() if self.settings_service else 0, parent=self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.notify('اطلاعات چهره ذخیره شد.')
        self.with_selected(enroll)

    def with_selected(self, action):
        internal_id = self.selected_id()
        if internal_id is None:
            return
        try:
            action(self.service.get(internal_id))
        except AppError as error:
            self.notify(str(error), True)

    def archive_selected(self):
        internal_id = self.selected_id()
        if internal_id is None:
            return
        if not confirm(self, 'غیرفعال‌سازی فرد', 'فرد انتخاب‌شده بایگانی و از فهرست فعال خارج می‌شود. اطلاعات او نگه‌داری خواهد شد.', 'غیرفعال‌سازی'):
            return
        try:
            self.service.archive(internal_id)
        except AppError as error:
            self.notify(str(error), True)
        else:
            self.refresh()
            self.notify('فرد بایگانی شد. اطلاعات او محفوظ است.')
