from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from PySide6.QtCore import QDate, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QDateTimeEdit
from attendance_app.application.people_service import PeopleService
from attendance_app.application.storage_service import StorageService
from attendance_app.configuration.settings import AppConfig
from attendance_app.storage.backup import BackupManager
from attendance_app.ui.main_window import MainWindow
from attendance_app.application.attendance_service import AttendanceService
from attendance_app.domain.errors import StorageError
from attendance_app.domain.people import PersonInput
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.ui.dialogs.attendance import AttendanceDetailsDialog
from attendance_app.ui.formatting import PERSIAN_CALENDAR
from attendance_app.ui.pages.history import HistoryPage


class HistoryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owns_app = QApplication.instance() is None
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    @classmethod
    def tearDownClass(cls):
        if cls.owns_app:
            import shiboken6
            shiboken6.delete(cls.app)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / 'history.db')
        self.db.initialize()
        self.people = PeopleRepository(self.db)
        self.person = self.people.create(PersonInput('علي', 'كريمي', '0012'))
        self.other = self.people.create(PersonInput('مریم', 'احمدی', '002'))
        self.repo = AttendanceRepository(self.db)
        self.service = AttendanceService(self.repo)
        self.page = HistoryPage(self.service)
        self.page.resize(640, 590)
        self.page.show()

    def tearDown(self):
        self.page.shutdown()
        self.wait(lambda: self.page.presenter.worker is None)
        self.page.close()
        self.page.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def wait(self, predicate):
        for _ in range(250):
            self.app.processEvents()
            if predicate():
                return
            QTest.qWait(20)
        self.fail('History did not reach expected state')

    def settled(self):
        self.wait(lambda: self.page.presenter.worker is None and not self.page.timer.isActive())

    def insert(self, person, day):
        with self.db.connect(write=True) as connection:
            connection.execute('''INSERT INTO attendance
                (person_id,attendance_date,attendance_time,observed_at,status,created_at)
                VALUES (?,?, '23:59:59+03:30',?,'present',?)''',
                (person.id, day, day + 'T20:29:59+00:00', day + 'T20:30:00+00:00'))

    def test_table_search_person_solar_day_range_reset_details(self):
        for person, day in ((self.person, '2026-10-27'), (self.person, '2026-10-28'),
                            (self.other, '2026-10-28')):
            self.insert(person, day)
        self.people.archive(self.other.id)
        self.page.refresh()
        self.settled()
        self.assertEqual(self.page.objectName(), 'page_history')
        self.assertEqual(self.page.model.rowCount(), 3)
        self.assertEqual(self.page.person.count(), 3)
        self.assertIn('بایگانی‌شده', self.page.person.itemText(self.page.person.findData(self.other.id)))
        self.assertEqual(self.page.model.data(self.page.model.index(2, 2)), '1405/08/05')
        self.page.search.setText('  علی   کریمی  ')
        self.settled()
        self.assertEqual(self.page.model.rowCount(), 2)
        self.page.start_date.setDate(QDate(1405, 8, 5, PERSIAN_CALENDAR))
        self.page.date_mode.setCurrentIndex(1)
        self.settled()
        self.assertEqual(self.page.start_date.text(), '1405/08/05')
        self.assertEqual(self.page.model.rowCount(), 1)
        QTest.mouseClick(self.page.table.viewport(), Qt.MouseButton.LeftButton,
                         pos=self.page.table.visualRect(self.page.model.index(0, 0)).center())
        self.assertTrue(self.page.details_button.isEnabled())
        dialog = AttendanceDetailsDialog(self.page.model.records[0], self.page)
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        self.assertIn('1405/08/05', texts)
        self.assertFalse(any('2026' in text for text in texts))
        dialog.close()
        self.page.end_date.setDate(QDate(1405, 8, 6, PERSIAN_CALENDAR))
        self.page.date_mode.setCurrentIndex(2)
        self.settled()
        self.assertEqual(self.page.model.rowCount(), 2)
        self.page.person.setCurrentIndex(self.page.person.findData(self.other.id))
        self.settled()
        self.assertEqual(self.page.model.rowCount(), 0)
        self.page.reset_button.click()
        self.settled()
        self.assertEqual(self.page.model.rowCount(), 3)
        self.assertEqual(self.page.date_mode.currentIndex(), 0)
        self.assertEqual(self.page.search.text(), '')

    def test_empty_invalid_range_read_failure_and_recovery(self):
        self.page.refresh()
        self.settled()
        self.assertEqual(self.page.state.text(), 'هنوز حضوری ثبت نشده است.')
        self.insert(self.person, '2026-10-27')
        self.page.start_date.setDate(QDate(2026, 10, 26))
        self.page.date_mode.setCurrentIndex(1)
        self.settled()
        self.assertIn('فیلتر', self.page.state.text())
        self.page.end_date.setDate(QDate(2026, 10, 25))
        self.page.date_mode.setCurrentIndex(2)
        self.settled()
        self.assertTrue(self.page.feedback.isVisible())
        with patch.object(self.service, 'search_history', side_effect=StorageError()):
            self.page.reset_filters()
            self.settled()
            self.assertTrue(self.page.feedback.isVisible())
            self.assertIn('دریافت سوابق ممکن نشد', self.page.state.text())
        self.page.refresh_button.click()
        self.settled()
        self.assertFalse(self.page.feedback.isVisible())
        self.assertEqual(self.page.model.rowCount(), 1)

    def test_slow_read_latest_filters_restore_invalidation_and_shutdown(self):
        self.insert(self.person, '2026-10-27')
        entered, release = Event(), Event()
        real = self.service.search_history
        def slow(**filters):
            entered.set()
            if not release.wait(4):
                raise RuntimeError('Timed out')
            return real(**filters)
        try:
            with patch.object(self.service, 'search_history', side_effect=slow):
                self.page.refresh()
                self.wait(entered.is_set)
                self.assertIn('دریافت', self.page.state.text())
                # UI event loop continues; stale first result must not overwrite newer input.
                self.page.search.setText('missing')
                QTest.qWait(220)
                release.set()
                self.settled()
                self.assertEqual(self.page.model.rowCount(), 0)
            # Same refresh hook is called after restore and when entering History.
            self.page.reset_filters()
            self.settled()
            self.assertEqual(self.page.model.rowCount(), 1)
            self.people.update(self.person.id, PersonInput('نام', 'جدید', '0009'))
            self.page.refresh()
            self.settled()
            self.assertEqual(self.page.model.records[0].public_person_id, '0009')
            entered.clear()
            release.clear()
            with patch.object(self.service, 'search_history', side_effect=slow):
                self.page.refresh()
                self.wait(entered.is_set)
                self.assertFalse(self.page.shutdown())
                release.set()
                self.settled()
                self.assertEqual(self.page.model.rowCount(), 0)
        finally:
            release.set()

    def test_numeric_picker_keyboard_and_leap_boundary(self):
        picker = self.page.start_date
        self.page.date_mode.setCurrentIndex(1)
        picker.setDate(QDate(1405, 8, 3, PERSIAN_CALENDAR))
        picker.setFocus()
        picker.setSelectedSection(QDateTimeEdit.Section.DaySection)
        QTest.keyClicks(picker, '05')
        QTest.keyClick(picker, Qt.Key.Key_Return)
        self.assertEqual(picker.text(), '1405/08/05')
        self.assertEqual(picker.date().toString('yyyy-MM-dd'), '2026-10-27')
        picker.setDate(QDate(1399, 12, 30, PERSIAN_CALENDAR))
        self.assertEqual(picker.text(), '1399/12/30')
        picker.setDate(picker.date().addDays(1))
        self.assertEqual(picker.text(), '1400/01/01')
        self.assertEqual(picker.date().toString('yyyy-MM-dd'), '2021-03-21')
        self.settled()

    def test_main_navigation_restore_refresh_and_close_during_read(self):
        backup = BackupManager(self.db)
        window = MainWindow(AppConfig(), PeopleService(self.people), StorageService(backup),
                            attendance_service=self.service)
        entered, release = Event(), Event()
        try:
            self.insert(self.person, '2026-10-27')
            path = Path(self.temp.name) / 'backup.db'
            backup.backup(path)
            window.show()
            window.navigate(3)
            page = window.history_page
            self.wait(lambda: page.presenter.worker is None)
            self.assertIs(window.pages.currentWidget(), page)
            self.assertEqual(page.objectName(), 'page_history')
            self.assertEqual(page.model.rowCount(), 1)
            self.insert(self.other, '2026-10-28')
            window.navigate(0)
            window.navigate(3)
            self.wait(lambda: page.presenter.worker is None)
            self.assertEqual(page.model.rowCount(), 2)
            backup.restore(path, confirmed=True)
            window.pages.widget(5).restored.emit()
            self.wait(lambda: page.presenter.worker is None)
            self.assertEqual(page.model.rowCount(), 1)
            real = self.service.search_history
            def slow(**filters):
                entered.set()
                if not release.wait(4):
                    raise RuntimeError('Timed out')
                return real(**filters)
            with patch.object(self.service, 'search_history', side_effect=slow):
                page.refresh()
                self.wait(entered.is_set)
                window.close()
                self.assertTrue(window.isVisible())
                release.set()
                self.wait(lambda: not window.isVisible() and page.presenter.worker is None)
        finally:
            release.set()
            window.close()
            self.wait(lambda: window.history_page.presenter.worker is None)
            window.deleteLater()
            self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
