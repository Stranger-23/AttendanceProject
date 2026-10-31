from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractItemView
from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.people_service import PeopleService
from attendance_app.application.storage_service import StorageService
from attendance_app.configuration.settings import AppConfig
from attendance_app.domain.errors import StorageError
from attendance_app.domain.people import PersonInput
from attendance_app.storage.backup import BackupManager
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.ui.main_window import MainWindow
from attendance_app.ui.pages.dashboard import DashboardPage


class DashboardUiTests(unittest.TestCase):
    DAY = '2026-10-27'

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
        self.db = Database(Path(self.temp.name) / 'dashboard.db')
        self.db.initialize()
        self.people = PeopleRepository(self.db)
        self.service = AttendanceService(AttendanceRepository(self.db))
        self.day = [self.DAY]
        self.page = DashboardPage(self.service, day_clock=lambda: self.day[0])
        self.page.resize(944, 640)
        self.page.show()

    def tearDown(self):
        self.page.shutdown()
        self.wait(lambda: self.page.presenter.worker is None)
        self.page.close()
        self.page.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def wait(self, predicate):
        for _ in range(300):
            self.app.processEvents()
            if predicate():
                return
            QTest.qWait(20)
        self.fail('Dashboard did not reach expected state')

    def settled(self, page=None):
        page = page or self.page
        self.wait(lambda: page.presenter.worker is None)

    def person(self, identifier):
        return self.people.create(PersonInput('علی', 'کریمی', identifier))

    def insert(self, person, day=DAY):
        with self.db.connect(write=True) as connection:
            connection.execute('''INSERT INTO attendance
                (person_id,attendance_date,attendance_time,observed_at,status,created_at)
                VALUES (?,?,'08:30:00+03:30',?,'present',?)''',
                (person.id, day, day + 'T05:00:00+00:00', day + 'T05:00:01+00:00'))

    def counts(self, page=None):
        return tuple(value.text() for value in (page or self.page).values.values())

    def test_population_table_solar_dates_readonly_and_desktop_reflow(self):
        a, b, c = [self.person(identifier) for identifier in ('0001', '0002', '0003')]
        self.insert(a, '2026-10-26')
        self.insert(a)
        self.insert(c)
        self.people.archive(c.id)
        self.page.refresh()
        self.settled()
        self.assertEqual(self.page.objectName(), 'page_dashboard')
        self.assertEqual(self.counts(), ('3', '2', '2', '3'))
        self.assertIn('1405/08/05', self.page.date_label.text())
        self.assertNotIn('2026', self.page.date_label.text())
        self.assertEqual(self.page.model.rowCount(), 3)
        self.assertEqual(self.page.model.data(self.page.model.index(0, 1)), '0003')
        self.assertEqual(self.page.model.data(self.page.model.index(0, 2)), '1405/08/05')
        self.assertEqual(self.page.model.data(self.page.model.index(0, 3)), '08:30:00')
        self.assertEqual(self.page.model.data(self.page.model.index(0, 4)), 'حاضر')
        self.assertEqual(self.page.table.editTriggers(), QAbstractItemView.EditTrigger.NoEditTriggers)
        self.assertFalse(self.page.table.isSortingEnabled())
        self.assertEqual(self.page.card_columns, 4)
        self.page.resize(624, 440)
        self.app.processEvents()
        self.assertEqual(self.page.card_columns, 2)
        self.assertTrue(self.page.scroll.verticalScrollBar().maximum() > 0)
        self.assertEqual(self.page.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.people.archive(a.id)
        self.people.archive(b.id)
        self.page.refresh_button.click()
        self.settled()
        self.assertEqual(self.counts(), ('3', '0', '2', '3'))

    def test_empty_people_only_older_attendance_and_recent_limit(self):
        self.page.refresh()
        self.settled()
        self.assertEqual(self.counts(), ('0', '0', '0', '0'))
        self.assertEqual(self.page.state.text(), 'هنوز حضوری ثبت نشده است.')
        for number in range(12):
            self.person(f'{number:04}')
        self.page.refresh()
        self.settled()
        self.assertEqual(self.counts(), ('12', '12', '0', '0'))
        for person in self.people.list_active():
            self.insert(person, '2026-10-26')
        self.page.refresh()
        self.settled()
        self.assertEqual(self.counts(), ('12', '12', '0', '12'))
        self.assertEqual(self.page.model.rowCount(), 10)

    def test_loading_error_retry_does_not_show_fake_zero(self):
        self.person('01')
        entered, release = Event(), Event()
        real = self.service.get_dashboard_snapshot
        def slow(day):
            entered.set()
            if not release.wait(4):
                raise RuntimeError('Timed out')
            return real(day)
        try:
            with patch.object(self.service, 'get_dashboard_snapshot', side_effect=slow):
                self.page.refresh()
                self.wait(entered.is_set)
                self.assertEqual(self.counts(), ('—',) * 4)
                self.assertIn('دریافت', self.page.state.text())
                self.assertEqual(self.page.model.rowCount(), 0)
                release.set()
                self.settled()
            with patch.object(self.service, 'get_dashboard_snapshot', side_effect=StorageError()):
                self.page.refresh()
                self.settled()
                self.assertEqual(self.counts(), ('—',) * 4)
                self.assertTrue(self.page.feedback.isVisible())
            self.page.refresh_button.click()
            self.settled()
            self.assertEqual(self.counts(), ('1', '1', '0', '0'))
            self.assertFalse(self.page.feedback.isVisible())
        finally:
            release.set()

    def test_coalesced_requests_and_obsolete_result_rejection(self):
        person = self.person('01')
        entered, release = Event(), Event()
        real = self.service.get_dashboard_snapshot
        calls, loaded = [], []
        self.page.presenter.loaded.connect(loaded.append)
        def slow(day):
            calls.append(day)
            result = real(day)
            if len(calls) == 1:
                entered.set()
                if not release.wait(4):
                    raise RuntimeError('Timed out')
            return result
        try:
            with patch.object(self.service, 'get_dashboard_snapshot', side_effect=slow):
                self.page.refresh()
                self.wait(entered.is_set)
                self.insert(person)
                for _ in range(10):
                    self.page.refresh()
                release.set()
                self.settled()
            self.assertEqual(len(calls), 2)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(self.counts(), ('1', '1', '1', '1'))
        finally:
            release.set()

    def test_midnight_result_ignored_then_visible_day_check(self):
        self.insert(self.person('01'))
        entered, release = Event(), Event()
        real = self.service.get_dashboard_snapshot
        loaded, calls = [], []
        self.page.presenter.loaded.connect(loaded.append)
        def slow(day):
            calls.append(day)
            result = real(day)
            if len(calls) == 1:
                entered.set()
                if not release.wait(4):
                    raise RuntimeError('Timed out')
            return result
        try:
            with patch.object(self.service, 'get_dashboard_snapshot', side_effect=slow):
                self.page.refresh()
                self.wait(entered.is_set)
                self.day[0] = '2026-10-28'
                release.set()
                self.settled()
            self.assertEqual(calls, ['2026-10-27', '2026-10-28'])
            self.assertEqual([s.captured_day for s in loaded], ['2026-10-28'])
            self.assertEqual(self.page.values['today_attendance'].text(), '0')
            self.assertIn('1405/08/06', self.page.date_label.text())
            self.day[0] = '2026-10-29'
            self.page.check_day()
            self.settled()
            self.assertEqual(self.page.snapshot.captured_day, '2026-10-29')
        finally:
            release.set()

    def window(self):
        people = PeopleService(self.people)
        return MainWindow(AppConfig(), people, StorageService(BackupManager(self.db)),
                          EnrollmentService(people, FaceTemplateRepository(self.db)), self.service)

    def close_window(self, window):
        window.close()
        self.wait(lambda: window.dashboard_page.presenter.worker is None and window.history_page.presenter.worker is None)
        window.close()
        window.deleteLater()
        self.app.processEvents()

    def test_landing_navigation_reactivation_and_restore(self):
        person = self.person('01')
        self.insert(person)
        backup = BackupManager(self.db)
        path = Path(self.temp.name) / 'backup.db'
        backup.backup(path)
        window = self.window()
        try:
            window.dashboard_page.presenter.day_clock = lambda: self.DAY
            window.show()
            window.dashboard_page.refresh()
            self.settled(window.dashboard_page)
            self.assertIs(window.pages.currentWidget(), window.dashboard_page)
            self.assertEqual(self.counts(window.dashboard_page), ('1', '1', '1', '1'))
            for key, index in (('attendance', 1), ('people', 2), ('history', 3)):
                window.dashboard_page.quick_buttons[key].click()
                self.assertEqual(window.pages.currentIndex(), index)
                self.assertIsNone(QApplication.activeModalWidget())
                window.navigate(0)
            self.settled(window.dashboard_page)
            window.dashboard_page.history_button.click()
            self.assertEqual(window.pages.currentIndex(), 3)
            self.insert(person, '2026-10-26')
            window.navigate(0)
            self.settled(window.dashboard_page)
            self.assertEqual(window.dashboard_page.snapshot.total_attendance, 2)
            backup.restore(path, confirmed=True)
            window.pages.widget(5).restored.emit()
            self.settled(window.dashboard_page)
            self.assertEqual(window.dashboard_page.snapshot.total_attendance, 1)
            self.person('02')
            # Deterministic activation event: production checks the real window activation state.
            with patch.object(window, 'isActiveWindow', return_value=True):
                QApplication.sendEvent(window, QEvent(QEvent.Type.ActivationChange))
            self.settled(window.dashboard_page)
            self.assertEqual(window.dashboard_page.snapshot.active_people, 2)
        finally:
            self.close_window(window)

    def test_main_close_waits_for_both_readers(self):
        window = self.window()
        dash_entered, history_entered = Event(), Event()
        dash_release, history_release = Event(), Event()
        real_dash, real_history = self.service.get_dashboard_snapshot, self.service.search_history
        def dashboard(day):
            dash_entered.set()
            if not dash_release.wait(5):
                raise RuntimeError('Timed out')
            return real_dash(day)
        def history(**filters):
            history_entered.set()
            if not history_release.wait(5):
                raise RuntimeError('Timed out')
            return real_history(**filters)
        try:
            window.show()
            self.settled(window.dashboard_page)
            with patch.object(self.service, 'get_dashboard_snapshot', side_effect=dashboard), \
                    patch.object(self.service, 'search_history', side_effect=history):
                window.dashboard_page.refresh()
                window.history_page.refresh()
                self.wait(lambda: dash_entered.is_set() and history_entered.is_set())
                window.close()
                self.assertTrue(window.isVisible())
                dash_release.set()
                self.settled(window.dashboard_page)
                self.assertTrue(window.isVisible())
                history_release.set()
                self.wait(lambda: not window.isVisible())
        finally:
            dash_release.set()
            history_release.set()
            self.close_window(window)


if __name__ == '__main__':
    unittest.main()
