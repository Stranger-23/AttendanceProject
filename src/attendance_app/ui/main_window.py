"""Presentation-only shell with right-side Persian navigation."""
import logging
from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)
from attendance_app.ui.components.cards import Card
from attendance_app.ui.components.icons import icon
from attendance_app.ui.pages.placeholder import PlaceholderPage
from attendance_app.ui.styles.theme import add_soft_shadow
from attendance_app.ui.pages.people import PeoplePage
from attendance_app.ui.pages.recognition import RecognitionPage
from attendance_app.ui.pages.storage_settings import StorageSettingsPage
from attendance_app.ui.pages.history import HistoryPage
from attendance_app.ui.pages.dashboard import DashboardPage
from attendance_app.ui.pages.reports import ReportsPage
from attendance_app.application.report_service import ReportService
from attendance_app.application.export_service import ExportService
from attendance_app.ui.formatting import attendance_date

PAGES = (
    ("dashboard", "داشبورد", "نمای کلی سامانه حضور و غیاب در این بخش نمایش داده خواهد شد."),
    ("attendance", "حضور و غیاب", "بخش حضور و غیاب هنوز آماده نیست."),
    ("people", "افراد", "مدیریت اطلاعات افراد در این بخش قرار خواهد گرفت."),
    ("history", "تاریخچه حضور و غیاب", "سوابق حضور و غیاب در این بخش نمایش داده خواهد شد."),
    ("reports", "گزارش‌ها", "گزارش‌های حضور و غیاب در این بخش قرار خواهند گرفت."),
    ("settings", "تنظیمات", "تنظیمات سامانه در این بخش قرار خواهند گرفت."),
)


class MainWindow(QMainWindow):
    def __init__(self, config, people_service, storage_service, enrollment_service=None, attendance_service=None,
                 *, report_service=None, export_service=None, settings_service=None):
        super().__init__()
        self.setWindowTitle(config.title)
        self.resize(config.width, config.height)
        self.setMinimumSize(config.minimum_width, config.minimum_height)
        self.setWindowIcon(icon("attendance", True))
        workspace = QWidget()
        workspace.setObjectName("workspace")
        self.setCentralWidget(workspace)
        # QHBoxLayout follows the application's RTL direction: first item is rightmost.
        row = QHBoxLayout(workspace)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(272)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(24, 32, 24, 24)
        sidebar_layout.setSpacing(8)
        brand = QLabel("سامانه حضور و غیاب")
        brand.setProperty("role", "brand")
        sidebar_layout.addWidget(brand)
        subtitle = QLabel("مدیریت حضور و غیاب")
        subtitle.setProperty("role", "muted")
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(16)
        self.navigation = QButtonGroup(self)
        self.navigation.setExclusive(True)
        self.buttons = []
        for index, (key, title, _) in enumerate(PAGES):
            if index in (0, 3, 5):
                group_title = QLabel({0: "اصلی", 3: "سوابق و گزارش‌ها", 5: "سامانه"}[index])
                group_title.setProperty("role", "section")
                group_title.setContentsMargins(16, 0, 16, 0)
                sidebar_layout.addSpacing(24 if index else 8)
                sidebar_layout.addWidget(group_title)
            button = QPushButton(title)
            button.setObjectName("nav_" + key)
            button.setProperty("nav", True)
            button.setAccessibleName(title)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(icon(key))
            button.setIconSize(QSize(22, 22))
            self.navigation.addButton(button, index)
            self.buttons.append(button)
            sidebar_layout.addWidget(button)
        sidebar_layout.addStretch()
        footer = QLabel("نسخه اولیه · مرحله پایه")
        footer.setProperty("role", "footnote")
        footer.setContentsMargins(8, 0, 8, 0)
        sidebar_layout.addWidget(footer)
        row.addWidget(self.sidebar)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(32, 32, 32, 32)
        body.setSpacing(24)
        header = Card()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(24)
        header.setMinimumHeight(96)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        self.page_title = QLabel()
        self.page_title.setProperty("role", "title")
        self.page_title.setWordWrap(True)
        titles.addWidget(self.page_title)
        caption = QLabel("سامانه مدیریت حضور و غیاب")
        caption.setProperty("role", "muted")
        titles.addWidget(caption)
        header_layout.addLayout(titles)
        header_layout.addStretch()
        badge = QLabel("پیش‌نمایش اولیه")
        badge.setProperty("role", "badge")
        header_layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        add_soft_shadow(header)
        body.addWidget(header)
        self.pages = QStackedWidget()
        self.history_page = HistoryPage(attendance_service) if attendance_service is not None else None
        self.dashboard_page = DashboardPage(attendance_service) if attendance_service is not None else None
        self.reports_page = ReportsPage(report_service or ReportService(attendance_service),
                                       export_service or ExportService(attendance_date)) if attendance_service is not None else None
        self._closing = False
        if self.history_page is not None:
            self.history_page.presenter.idle.connect(self._readers_idle)
        if self.reports_page is not None:
            self.reports_page.presenter.idle.connect(self._readers_idle)
        if self.dashboard_page is not None:
            self.dashboard_page.presenter.idle.connect(self._readers_idle)
            self.dashboard_page.navigate_requested.connect(self.navigate_to)
        for key, title, description in PAGES:
            if key == 'dashboard' and self.dashboard_page is not None:
                self.pages.addWidget(self.dashboard_page)
            elif key == 'people':
                self.people_page = PeoplePage(people_service, enrollment_service=enrollment_service, model_dir=config.model_dir, settings_service=settings_service)
                self.pages.addWidget(self.people_page)
            elif key == 'attendance' and enrollment_service is not None:
                self.pages.addWidget(RecognitionPage(config.model_dir, enrollment_service.templates, attendance_service, settings_service=settings_service))
            elif key == 'history' and self.history_page is not None:
                self.pages.addWidget(self.history_page)
            elif key == 'reports' and self.reports_page is not None:
                self.pages.addWidget(self.reports_page)
            elif key == 'settings':
                settings_page = StorageSettingsPage(storage_service, settings_service=settings_service, app_name=config.title)
                settings_page.restored.connect(self.people_page.refresh)
                if self.history_page is not None:
                    settings_page.restored.connect(self.history_page.refresh)
                if self.dashboard_page is not None:
                    settings_page.restored.connect(self.dashboard_page.refresh)
                if self.reports_page is not None:
                    settings_page.restored.connect(self.reports_page.refresh)
                self.pages.addWidget(settings_page)
            else:
                self.pages.addWidget(PlaceholderPage(key, title, description))
        body.addWidget(self.pages, 1)
        row.addWidget(content, 1)
        self.navigation.idClicked.connect(self.navigate)
        self.navigate(0)

    def navigate(self, index: int) -> None:
        if not 0 <= index < len(PAGES):
            raise IndexError("Unknown navigation page")
        self.pages.setCurrentIndex(index)
        if PAGES[index][0] == "people":
            self.people_page.refresh()
        if PAGES[index][0] == "history" and self.history_page is not None:
            self.history_page.refresh()
        if PAGES[index][0] == "dashboard" and self.dashboard_page is not None:
            self.dashboard_page.refresh()
        if PAGES[index][0] == "reports" and self.reports_page is not None:
            self.reports_page.refresh()
        self.page_title.setText(PAGES[index][1])
        for position, button in enumerate(self.buttons):
            selected = position == index
            button.setChecked(selected)
            button.setIcon(icon(PAGES[position][0], selected))
        logging.getLogger("attendance_app.ui").info("Navigated to %s", PAGES[index][0])

    def navigate_to(self, key):
        self.navigate(next(index for index, page in enumerate(PAGES) if page[0] == key))

    def changeEvent(self, event):
        super().changeEvent(event)
        if (event.type() == QEvent.Type.ActivationChange and self.isActiveWindow()
                and not getattr(self, '_closing', False)
                and getattr(self, 'dashboard_page', None) is not None
                and self.pages.currentWidget() is self.dashboard_page):
            self.dashboard_page.refresh()

    def _readers_idle(self):
        if self._closing:
            self.close()

    def closeEvent(self, event):
        self._closing = True
        ready = True
        for page in (self.history_page, self.dashboard_page, self.reports_page):
            if page is not None and not page.shutdown():
                ready = False
        if not ready:
            event.ignore()
            return
        super().closeEvent(event)
