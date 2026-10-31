from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QTextEdit, QVBoxLayout, QWidget,
)
from attendance_app.domain.errors import AppError
from attendance_app.domain.people import PersonInput
from attendance_app.ui.formatting import registration_date


def plain_label(text='', role=None):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if role:
        label.setProperty('role', role)
    return label


def confirm(parent, title, message, action):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(400)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(24)
    layout.addWidget(plain_label(message))
    row = QHBoxLayout()
    yes = QPushButton(action)
    yes.setObjectName('confirm_action')
    yes.setProperty('variant', 'primary')
    no = QPushButton('انصراف')
    no.setObjectName('cancel_action')
    yes.clicked.connect(dialog.accept)
    no.clicked.connect(dialog.reject)
    no.setDefault(True)
    row.addWidget(yes)
    row.addWidget(no)
    layout.addLayout(row)
    return dialog.exec() == QDialog.DialogCode.Accepted


class PersonFormDialog(QDialog):
    saved = Signal(object)

    def __init__(self, service, person=None, parent=None):
        super().__init__(parent)
        self.service, self.person = service, person
        title = 'ویرایش فرد' if person else 'افزودن فرد'
        self.setWindowTitle(title)
        self.setObjectName('person_form')
        self.resize(480, 620)
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(plain_label(title, 'heading'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("dialog_content")
        fields = QVBoxLayout(content)
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setSpacing(12)
        self.first_name = QLineEdit(person.first_name if person else '')
        self.last_name = QLineEdit(person.last_name if person else '')
        self.person_id = QLineEdit(person.person_id if person else '')
        # IDs are text, without a numeric validator or digit conversion.
        self.optional_info = QTextEdit()
        self.optional_info.setAcceptRichText(False)
        self.optional_info.setPlainText(person.optional_info if person else '')
        self.optional_info.setMinimumHeight(80)
        for key, text, field in (
            ('first_name', 'نام', self.first_name), ('last_name', 'نام خانوادگی', self.last_name),
            ('person_id', 'شناسه فرد / دانشجو', self.person_id),
            ('optional_info', 'اطلاعات تکمیلی (اختیاری)', self.optional_info),
        ):
            field.setObjectName(key)
            field.setAccessibleName(text)
            if isinstance(field, QLineEdit):
                field.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
            label = plain_label(text)
            label.setBuddy(field)
            fields.addWidget(label)
            fields.addWidget(field)
        fields.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.error = plain_label('', 'error')
        self.error.setObjectName('form_error')
        self.error.hide()
        layout.addWidget(self.error)
        actions = QHBoxLayout()
        self.save_button = QPushButton('ثبت')
        self.save_button.setObjectName('save_person')
        self.save_button.setProperty('variant', 'primary')
        self.save_button.setDefault(True)
        self.cancel_button = QPushButton('انصراف')
        self.cancel_button.setAutoDefault(False)
        actions.addWidget(self.save_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.reject)

    def save(self):
        self.save_button.setEnabled(False)
        try:
            data = PersonInput(self.first_name.text(), self.last_name.text(), self.person_id.text(), self.optional_info.toPlainText())
            person = self.service.update(self.person.id, data) if self.person else self.service.create(data)
        except AppError as error:
            self.error.setText(str(error))
            self.error.show()
        else:
            self.saved.emit(person)
            self.accept()
        finally:
            self.save_button.setEnabled(True)


class PersonDetailsDialog(QDialog):
    def __init__(self, person, parent=None, *, face_status=None):
        super().__init__(parent)
        self.setWindowTitle('جزئیات فرد')
        self.setObjectName('person_details')
        self.resize(480, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(plain_label('جزئیات فرد', 'heading'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("dialog_content")
        fields = QVBoxLayout(content)
        fields.setSpacing(12)
        for title, value in (
            ('نام و نام خانوادگی', person.full_name), ('شناسه', person.person_id),
            ('تاریخ ثبت (میلادی)', registration_date(person.created_at)),
            ('وضعیت', 'فعال' if person.is_active else 'بایگانی‌شده'),
            ('اطلاعات تکمیلی', person.optional_info or 'وارد نشده است'),
        ):
            fields.addWidget(plain_label(title, 'muted'))
            label = plain_label(value)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            fields.addWidget(label)
        fields.addStretch()
        if face_status is not None:
            fields.insertWidget(fields.count()-1, plain_label('اطلاعات چهره', 'muted'))
            fields.insertWidget(fields.count()-1, plain_label(face_status))
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        close = QPushButton('بستن')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
