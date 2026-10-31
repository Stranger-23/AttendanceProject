"""Composition root: configuration, diagnostics, theme, and the UI shell."""
import logging
import sys
from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from attendance_app.configuration.settings import AppConfig
from attendance_app.configuration.logging_setup import configure_logging
from attendance_app.ui.styles.theme import apply_theme
from attendance_app.ui.main_window import MainWindow
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.storage.backup import BackupManager
from attendance_app.application.people_service import PeopleService
from attendance_app.application.storage_service import StorageService
from attendance_app.application.settings_service import SettingsService
from attendance_app.storage.repositories.settings import SettingsRepository
from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.report_service import ReportService
from attendance_app.application.export_service import ExportService
from attendance_app.ui.formatting import attendance_date
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository


def create_application(argv=None, config=None):
    config = config or AppConfig()
    configure_logging(config.data_dir)
    QLocale.setDefault(QLocale(QLocale.Language.Persian, QLocale.Country.Iran))
    app = QApplication(argv or [])
    app.setApplicationName("SmartAttendance")
    app.setApplicationDisplayName(config.title)
    app.setOrganizationName("SmartAttendance")
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    family = apply_theme(app, config.font_dir)
    logger = logging.getLogger("attendance_app")
    logger.info("Application initialized; font=%s; direction=RTL", family)

    def report_exception(kind, value, traceback):
        logger.critical("Unhandled exception", exc_info=(kind, value, traceback))
        QMessageBox.critical(None, "Ø®Ø·Ø§ÛŒ Ø¨Ø±Ù†Ø§Ù…Ù‡", "Ø®Ø·Ø§ÛŒ ØºÛŒØ±Ù…Ù†ØªØ¸Ø±Ù‡â€ŒØ§ÛŒ Ø±Ø® Ø¯Ø§Ø¯. Ø¬Ø²Ø¦ÛŒØ§Øª Ø¯Ø± Ú¯Ø²Ø§Ø±Ø´ Ø¨Ø±Ù†Ø§Ù…Ù‡ Ø«Ø¨Øª Ø´Ø¯.")

    sys.excepthook = report_exception
    database = Database(config.database_path)
    database.initialize()
    people = PeopleService(PeopleRepository(database))
    enrollment = EnrollmentService(people, FaceTemplateRepository(database))
    attendance = AttendanceService(AttendanceRepository(database))
    window = MainWindow(config, people, StorageService(BackupManager(database)), enrollment, attendance,
                        settings_service=SettingsService(SettingsRepository(database)),
                        report_service=ReportService(attendance), export_service=ExportService(attendance_date))
    return app, window
