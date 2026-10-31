"""Render an isolated Reports shell; no real profile, camera, or workbook is read."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.people_service import PeopleService
from attendance_app.application.storage_service import StorageService
from attendance_app.configuration.settings import AppConfig
from attendance_app.domain.people import PersonInput
from attendance_app.storage.backup import BackupManager
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.ui.main_window import MainWindow
from attendance_app.ui.styles.theme import apply_theme


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle('Fusion')
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    apply_theme(app, AppConfig().font_dir)
    with TemporaryDirectory() as temp:
        database = Database(Path(temp) / 'preview.db')
        database.initialize()
        people = PeopleService(PeopleRepository(database))
        for identifier, name in (('000001', 'علی'), ('001234567890123456789', 'سارا')):
            person = people.create(PersonInput(name, 'نمونه', identifier))
            with database.connect(write=True) as connection:
                for day in ('2026-10-26', '2026-10-27'):
                    connection.execute('''INSERT INTO attendance
                        (person_id,attendance_date,attendance_time,observed_at,created_at)
                        VALUES (?,?,'08:30:00+03:30',?,?)''',
                        (person.id, day, day + 'T05:00:00+00:00', day + 'T05:00:01+00:00'))
        attendance = AttendanceService(AttendanceRepository(database))
        window = MainWindow(AppConfig(), people, StorageService(BackupManager(database)),
                            EnrollmentService(people, FaceTemplateRepository(database)), attendance)
        window.show()
        window.navigate_to('reports')
        for _ in range(300):
            app.processEvents()
            if window.reports_page.snapshot is not None and window.dashboard_page.presenter.worker is None:
                break
            QTest.qWait(20)
        else:
            raise RuntimeError('Preview did not load')
        for width, height in ((1280, 820), (960, 640)):
            window.resize(width, height)
            QTest.qWait(200)
            window.grab().save(str(output / f'reports-{width}.png'))
            scroll = window.reports_page.layout().itemAt(0).widget()
            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
            QTest.qWait(100)
            window.grab().save(str(output / f'reports-{width}-bottom.png'))
            scroll.verticalScrollBar().setValue(0)
        page = window.reports_page
        page.presenter.export_service.export(page.snapshot, output / 'preview-report.xlsx', overwrite=True)
        window.close()
        while window.isVisible():
            app.processEvents()
            QTest.qWait(20)


if __name__ == '__main__':
    main()
