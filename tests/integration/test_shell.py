"""Run on Windows with: python -m unittest discover -s tests/integration -v."""
import logging
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QFontInfo
from PySide6.QtTest import QTest
from attendance_app.bootstrap import create_application
from attendance_app.configuration.settings import AppConfig
from attendance_app.ui.main_window import PAGES
from PySide6.QtWidgets import QApplication, QDialog, QPushButton
from unittest.mock import patch
from attendance_app.ui.dialogs.people import PersonFormDialog, PersonDetailsDialog
from attendance_app.domain.people import PersonInput
from attendance_app.domain.errors import StorageError


class ShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.addClassCleanup(cls.close_log_handlers)

        @dataclass(frozen=True)
        class TestConfig(AppConfig):
            @property
            def data_dir(self):
                return Path(cls.temp.name)

        cls.app, cls.window = create_application([], TestConfig())
        cls.addClassCleanup(cls.close_window)
        cls.window.show()
        QTest.qWait(200)

    @classmethod
    def close_window(cls):
        cls.window.close()
        cls.app.processEvents()

    @classmethod
    def close_log_handlers(cls):
        logger = logging.getLogger("attendance_app")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_window_rtl_font_and_all_navigation(self):
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.app.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.assertEqual(self.window.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.assertGreater(self.window.sidebar.x(), self.window.pages.mapTo(self.window, self.window.pages.rect().topLeft()).x())
        family = self.app.font().family()
        self.assertIn("iransans", family.lower())
        self.assertIn(family, QFontDatabase.families())
        self.assertEqual(QFontInfo(self.app.font()).family(), family)
        for index, (key, title, _) in enumerate(PAGES):
            with self.subTest(page=key):
                QTest.mouseClick(self.window.buttons[index], Qt.MouseButton.LeftButton)
                self.app.processEvents()
                self.assertEqual(self.window.pages.currentIndex(), index)
                self.assertEqual(self.window.page_title.text(), title)
                self.assertEqual(self.window.pages.currentWidget().objectName(), "page_" + key)
                self.assertEqual(self.window.pages.currentWidget().layoutDirection(), Qt.LayoutDirection.RightToLeft)
                self.assertEqual(sum(button.isChecked() for button in self.window.buttons), 1)
        self.window.resize(960, 640)
        self.app.processEvents()
        for button in self.window.buttons:
            self.assertTrue(self.window.rect().contains(button.mapTo(self.window, button.rect().bottomRight())))


    def modal(self, trigger, action, expected=QDialog):
        errors = []
        handled = []
        def interact():
            handled.append(True)
            dialog = QApplication.activeModalWidget()
            try:
                self.assertIsInstance(dialog, expected)
                self.assertEqual(dialog.layoutDirection(), Qt.LayoutDirection.RightToLeft)
                action(dialog)
            except BaseException as error:
                errors.append(error)
                if dialog:
                    dialog.reject()
        QTimer.singleShot(50, interact)
        trigger()
        self.assertTrue(handled, "Expected modal dialog did not open")
        if errors:
            raise errors[0]

    def test_people_add_validate_search_details_edit_archive(self):
        self.window.navigate(2)
        page = self.window.people_page
        self.assertTrue(page.isVisible())
        page.search.clear()
        page.filter.setCurrentIndex(0)
        page.refresh()
        initial = page.model.rowCount()
        def add(dialog):
            QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)
            self.assertTrue(dialog.error.isVisible())
            self.assertTrue(dialog.isVisible())
            dialog.first_name.setText('علی')
            dialog.last_name.setText('احمدی')
            dialog.person_id.setText('000123')
            dialog.optional_info.setPlainText('اطلاعات آزمایشی')
            with patch.object(page.service, 'create', side_effect=StorageError()):
                dialog.save_button.click()
            self.assertTrue(dialog.isVisible())
            self.assertTrue(dialog.error.isVisible())
            self.assertEqual(dialog.person_id.text(), '000123')
            self.assertEqual(dialog.optional_info.toPlainText(), 'اطلاعات آزمایشی')
            QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.modal(page.add_button.click, add, PersonFormDialog)
        self.assertEqual(page.model.rowCount(), initial + 1)
        self.assertIn('ثبت شد', page.feedback.text())
        person = next(p for p in page.model.people if p.person_id == '000123')
        def duplicate(dialog):
            dialog.first_name.setText('نام')
            dialog.last_name.setText('تکراری')
            dialog.person_id.setText('000123')
            dialog.save_button.click()
            self.assertTrue(dialog.isVisible())
            self.assertIn('قبلاً', dialog.error.text())
            self.assertEqual(dialog.first_name.text(), 'نام')
            self.assertEqual(dialog.person_id.text(), '000123')
            dialog.cancel_button.click()
        self.modal(page.add_button.click, duplicate, PersonFormDialog)
        page.search.setText('000123')
        QTest.qWait(250)
        self.assertEqual(page.model.rowCount(), 1)
        self.assertEqual(page.model.people[0].id, person.id)
        QTest.qWait(50)
        QTest.mouseClick(page.table.viewport(), Qt.MouseButton.LeftButton, pos=page.table.visualRect(page.model.index(0, 0)).center())
        def details(dialog):
            from PySide6.QtWidgets import QLabel
            values = [label.text() for label in dialog.findChildren(QLabel)]
            self.assertIn('000123', values)
            self.assertIn('اطلاعات آزمایشی', values)
            dialog.accept()
        self.modal(page.details_button.click, details, PersonDetailsDialog)
        def edit(dialog):
            self.assertEqual(dialog.first_name.text(), 'علی')
            dialog.first_name.setText('رضا')
            dialog.save_button.click()
        self.modal(page.edit_button.click, edit, PersonFormDialog)
        self.assertEqual(page.model.people[0].first_name, 'رضا')
        self.assertEqual(page.model.people[0].created_at, person.created_at)
        QTest.qWait(50)
        QTest.mouseClick(page.table.viewport(), Qt.MouseButton.LeftButton, pos=page.table.visualRect(page.model.index(0, 0)).center())
        self.modal(page.archive_button.click, lambda dialog: dialog.findChild(QPushButton, 'cancel_action').click())
        self.assertEqual(page.model.rowCount(), 1)
        QTest.qWait(50)
        QTest.mouseClick(page.table.viewport(), Qt.MouseButton.LeftButton, pos=page.table.visualRect(page.model.index(0, 0)).center())
        self.modal(page.archive_button.click, lambda dialog: dialog.findChild(QPushButton, 'confirm_action').click())
        self.assertEqual(page.model.rowCount(), 0)
        self.assertFalse(page.service.get(person.id).is_active)
        page.filter.setCurrentIndex(1)
        self.assertEqual(page.model.rowCount(), 1)
        QTest.qWait(50)
        QTest.mouseClick(page.table.viewport(), Qt.MouseButton.LeftButton, pos=page.table.visualRect(page.model.index(0, 0)).center())
        self.assertFalse(page.archive_button.isEnabled())
        self.modal(page.details_button.click, lambda dialog: dialog.accept(), PersonDetailsDialog)
        page.search.clear()
        page.filter.setCurrentIndex(0)
        page.refresh()

    def test_storage_ui_backup_restore_and_validation(self):
        self.window.navigate(5)
        page = self.window.pages.currentWidget()
        people = self.window.people_page.service
        before = people.create(PersonInput('پیش', 'بازیابی', 'BACKUP-01'))
        backup_path = str(Path(self.temp.name) / 'ui-backup.db')
        with patch('attendance_app.ui.pages.storage_settings.QFileDialog.getSaveFileName', return_value=(backup_path, '')):
            page.backup_button.click()
        self.assertTrue(Path(backup_path).is_file())
        self.assertIn('ذخیره شد', page.feedback.text())
        after = people.create(PersonInput('پس', 'بازیابی', 'BACKUP-02'))
        with patch('attendance_app.ui.pages.storage_settings.QFileDialog.getOpenFileName', return_value=(backup_path, '')):
            self.modal(page.restore_button.click, lambda dialog: dialog.findChild(QPushButton, 'cancel_action').click())
        self.assertEqual(people.get(after.id), after)
        with patch('attendance_app.ui.pages.storage_settings.QFileDialog.getOpenFileName', return_value=(backup_path, '')):
            self.modal(page.restore_button.click, lambda dialog: dialog.findChild(QPushButton, 'confirm_action').click())
        self.assertIn('بازیابی شد', page.feedback.text())
        self.assertEqual(people.get(before.id), before)
        self.assertNotIn('BACKUP-02', [p.person_id for p in people.search()])
        bad_path = Path(self.temp.name) / 'bad-backup.db'
        bad_path.write_text('invalid')
        with patch('attendance_app.ui.pages.storage_settings.QFileDialog.getOpenFileName', return_value=(str(bad_path), '')):
            self.modal(page.restore_button.click, lambda dialog: dialog.findChild(QPushButton, 'confirm_action').click())
        self.assertIn('خطا', page.feedback.text())
        self.assertEqual(people.get(before.id), before)
        people.archive(before.id)


    def test_enrollment_capture_worker_save_cancel_and_failure(self):
        import threading
        import numpy as np
        from dataclasses import replace
        from PySide6.QtCore import QThread
        from attendance_app.recognition.engine import Analysis, RecognitionError
        from attendance_app.recognition.worker import CameraWorker
        from attendance_app.ui.dialogs.enrollment import FaceCaptureDialog

        page = self.window.people_page
        service = page.enrollment_service
        person = page.service.create(PersonInput('آزمایش', 'چهره', 'FACE-UI-001'))
        service.config = replace(service.config, sample_interval_seconds=0)
        main_thread = threading.get_ident()
        worker_threads = []
        released = []

        class TestCamera:
            def __init__(self, _index): pass
            def __enter__(self):
                worker_threads.append(threading.get_ident())
                return self
            def __exit__(self, *_): released.append(True)
            def read(self):
                QThread.msleep(10)
                return np.zeros((240,320,3), np.uint8)

        class TestEngine:
            def __init__(self, *_): worker_threads.append(threading.get_ident())
            def analyze(self, _frame, *, extract=False):
                return Analysis(np.empty((0,15),np.float32), 'ready', 'تصویر آزمایشی', 1,
                                embedding=np.eye(128,dtype=np.float32)[0] if extract else None)

        def make_worker(directory, config, index, parent):
            return CameraWorker(directory, config, index, parent, engine_factory=TestEngine, camera_factory=TestCamera)

        def wait_until(predicate):
            for _ in range(100):
                if predicate(): return
                QTest.qWait(20)
            self.fail('Worker did not reach expected state')

        dialog = FaceCaptureDialog(self.window.people_page.model_dir, service, person, parent=self.window, worker_factory=make_worker)
        dialog.show()
        self.assertEqual(dialog.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.assertIn('iransans', dialog.font().family().lower())
        dialog.start_button.click()
        wait_until(lambda: dialog.capture_button.isEnabled())
        for count in range(1, 4):
            dialog.capture_button.click()
            wait_until(lambda: len(dialog.samples) == count)
            if count < 3: wait_until(lambda: dialog.capture_button.isEnabled())
        self.assertTrue(dialog.save_button.isEnabled())
        with patch.object(service, 'save', wraps=service.save) as save:
            dialog.save_button.click()
            dialog.save_button.click()
            self.assertEqual(save.call_count, 1)
        wait_until(lambda: dialog.worker is None)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        rows = service.templates.list_for_person(person.id)
        self.assertEqual(len(rows), 3)
        self.assertTrue(released)
        self.assertTrue(all(identity != main_thread for identity in worker_threads))

        person, ids = service.begin(person.id)
        cancelled = FaceCaptureDialog(page.model_dir, service, person, ids, parent=self.window, worker_factory=make_worker)
        cancelled.show()
        cancelled.start_button.click()
        wait_until(lambda: cancelled.worker is not None and cancelled.capture_button.isEnabled())
        cancelled.reject()
        wait_until(lambda: cancelled.worker is None)
        self.assertEqual(service.templates.list_for_person(person.id), rows)

        replacement = FaceCaptureDialog(page.model_dir, service, person, ids, parent=self.window, worker_factory=make_worker)
        replacement.show()
        replacement.samples = [np.eye(128,dtype=np.float32)[1] for _ in range(3)]
        replacement.update_progress()
        self.modal(replacement.save_button.click, lambda confirm: confirm.findChild(QPushButton, 'cancel_action').click())
        self.assertEqual(service.templates.list_for_person(person.id), rows)
        self.modal(replacement.save_button.click, lambda confirm: confirm.findChild(QPushButton, 'confirm_action').click())
        self.assertNotEqual(service.templates.list_for_person(person.id)[0]['id'], rows[0]['id'])

        class BrokenCamera(TestCamera):
            def read(self): raise RecognitionError('خطای آزمایشی دوربین')

        failed = FaceCaptureDialog(page.model_dir, parent=self.window,
            worker_factory=lambda directory,config,index,parent: CameraWorker(directory,config,index,parent,engine_factory=TestEngine,camera_factory=BrokenCamera))
        failed.show()
        failed.start_button.click()
        wait_until(lambda: failed.worker is None)
        self.assertIn('خطای آزمایشی', failed.status.text())
        failed.reject()
        page.service.archive(person.id)

    def test_recognition_live_clock_updates_without_camera_and_stops_on_close(self):
        from datetime import datetime
        from unittest.mock import Mock
        from attendance_app.ui.dialogs.recognition import RecognitionDialog
        with patch('attendance_app.ui.dialogs.recognition.datetime') as clock:
            clock.now.return_value = datetime(2025, 3, 20, 23, 59, 59).astimezone()
            dialog = RecognitionDialog('.', Mock(), self.window)
            self.addCleanup(dialog.close)
            self.assertIn('1403/12/30', dialog.current_datetime.text())
            self.assertIn('23:59:59', dialog.current_datetime.text())
            dialog.show()
            self.assertTrue(dialog.clock_timer.isActive())
            self.assertEqual(dialog.clock_timer.interval(), 1000)
            self.assertIs(dialog.clock_timer.parent(), dialog)
            self.assertFalse(dialog.timer.isActive())
            clock.now.return_value = datetime(2025, 3, 21, 0, 0, 0).astimezone()
            for _ in range(120):
                if '00:00:00' in dialog.current_datetime.text():
                    break
                QTest.qWait(20)
            self.assertIn('1404/01/01', dialog.current_datetime.text())
            self.assertIn('00:00:00', dialog.current_datetime.text())
            dialog.camera_error('دوربین باز نشد.')
            self.assertTrue(dialog.current_datetime.isVisible())
            self.assertTrue(dialog.clock_timer.isActive())
            clock.now.return_value = datetime(2025, 3, 21, 0, 0, 1).astimezone()
            for _ in range(120):
                if '00:00:01' in dialog.current_datetime.text():
                    break
                QTest.qWait(20)
            self.assertIn('00:00:01', dialog.current_datetime.text())
            dialog.close()
            self.assertFalse(dialog.clock_timer.isActive())
            self.assertFalse(dialog.isVisible())
            # A reused dialog must restart its clock, then stop on accept too.
            dialog.show()
            self.assertTrue(dialog.clock_timer.isActive())
            dialog.accept()
            self.assertFalse(dialog.clock_timer.isActive())

    def test_recognition_preview_results_failure_restart_and_safe_close(self):
        import numpy as np
        from PySide6.QtCore import QThread
        from attendance_app.recognition.worker import RecognitionWorker
        from attendance_app.recognition.matching import RecognitionResult
        from attendance_app.recognition.engine import RecognitionError
        from attendance_app.ui.dialogs.recognition import RecognitionDialog
        from attendance_app.domain.face_templates import encode_embedding
        from attendance_app.recognition.engine import MODEL_ID, ALIGNMENT_ID
        from unittest.mock import Mock
        repository = Mock()
        repository.list_active.return_value = []
        dialog = RecognitionDialog('.', repository, self.window)
        dialog.show()
        def wait_until(predicate):
            for _ in range(100):
                if predicate(): return
                QTest.qWait(20)
            self.fail('Recognition worker did not reach expected state')
        dialog.start_button.click()
        wait_until(lambda: dialog.worker is None)
        self.assertTrue(dialog.clock_timer.isActive())
        self.assertTrue(dialog.current_datetime.isVisible())
        self.assertIn('ثبت نشده', dialog.status.text())
        self.assertTrue(dialog.start_button.isEnabled())
        class Packet:
            def take_latest(self):
                return np.zeros((240,320,3),np.uint8), [
                    RecognitionResult((10,40,100,100),'known',1,'حسین افشار',.8),
                    RecognitionResult((180,40,100,100))]
        dialog.worker = Packet()
        dialog.update_preview()
        self.assertIn('حسین افشار',dialog.status.text())
        self.assertIn('ناشناس',dialog.status.text())
        self.assertFalse(dialog.preview.pixmap().isNull())
        dialog.worker = None
        released = []
        class Camera:
            def __init__(self, *_): pass
            def __enter__(self): return self
            def __exit__(self, *_): released.append(True)
            def read(self):
                QThread.msleep(10)
                return np.zeros((240,320,3),np.uint8)
        class Engine:
            def __init__(self,*_): pass
            def analyze_all(self,frame): return []
        repository.list_active.return_value = [dict(person_id=1,first_name='حسین',last_name='افشار',
            embedding=encode_embedding(np.eye(128)[0]),dimensions=128,dtype='<f4',model_id=MODEL_ID,alignment_id=ALIGNMENT_ID)]
        dialog.worker_factory = lambda directory,templates,index,parent: RecognitionWorker(
            directory,templates,index,parent,engine_factory=Engine,camera_factory=Camera)
        dialog.start_button.click()
        wait_until(lambda: 'منتظر' in dialog.status.text())
        self.assertTrue(dialog.clock_timer.isActive())
        self.assertEqual(dialog.results,[])
        dialog.reject()
        wait_until(lambda: dialog.worker is None)
        self.assertTrue(released)
        self.assertFalse(dialog.isVisible())
        self.assertFalse(dialog.clock_timer.isActive())


    def test_attendance_commit_feedback_async_writer_and_database_failure(self):
        from threading import Event
        import numpy as np
        from unittest.mock import Mock
        from PySide6.QtCore import QThread
        from attendance_app.recognition.engine import Analysis
        from attendance_app.recognition.worker import RecognitionWorker
        from attendance_app.ui.dialogs.recognition import RecognitionDialog

        page = self.window.pages.widget(1)
        enrollment = self.window.people_page.enrollment_service
        person = self.window.people_page.service.create(PersonInput('آزمایش', 'حضور', 'ATTENDANCE-UI-001'))
        enrollment.save(person, [np.eye(128)[0]] * 3)
        entered, release = Event(), Event()
        frames, released = [], []
        class Camera:
            def __init__(self, *_): pass
            def __enter__(self): return self
            def __exit__(self, *_): released.append(True)
            def read(self):
                QThread.msleep(5)
                frames.append(True)
                return np.zeros((240, 320, 3), np.uint8)
        class Engine:
            def __init__(self, *_): pass
            def analyze_all(self, _):
                face = np.zeros((1, 15), np.float32)
                face[0, :4] = [10, 40, 100, 100]
                return [Analysis(face, 'ready', '', 0, embedding=np.eye(128)[0])]
        def make_worker(directory, templates, index, parent, **options):
            return RecognitionWorker(directory, templates, index, parent,
                                     engine_factory=Engine, camera_factory=Camera, **options)
        def wait_until(predicate):
            for _ in range(150):
                if predicate(): return
                QTest.qWait(20)
            self.fail('Attendance UI did not reach expected state')
        def slow_record(result, observed):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('Test writer not released')
            return page.attendance_service.record(result, observed)
        slow = Mock()
        slow.record.side_effect = slow_record
        dialog = RecognitionDialog('.', enrollment.templates, self.window,
                                   worker_factory=make_worker, attendance_service=slow)
        dialog.show()
        try:
            dialog.start_button.click()
            wait_until(lambda: entered.is_set() and len(frames) >= 20)
            self.assertEqual(dialog.attendance_feedback.text(), '')
            self.assertIn('آزمایش حضور', dialog.status.text())
            self.assertTrue(dialog.worker.isRunning())
            release.set()
            wait_until(lambda: 'ثبت شد' in dialog.attendance_feedback.text())
            QTest.qWait(100)
            self.assertEqual(slow.record.call_count, 1)
            self.assertEqual(dialog.attendance_feedback.text().count('ثبت شد'), 1)
            database = enrollment.templates.database
            with database.connect() as connection:
                rows = connection.execute('SELECT * FROM attendance WHERE person_id=?', (person.id,)).fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['status'], 'present')
        finally:
            release.set()
            dialog.reject()
            wait_until(lambda: dialog.worker is None)
        self.assertTrue(released)
        failed_service = Mock()
        failed_service.record.side_effect = StorageError()
        failed = RecognitionDialog('.', enrollment.templates, self.window,
                                   worker_factory=make_worker, attendance_service=failed_service)
        failed.show()
        try:
            failed.start_button.click()
            wait_until(lambda: 'ثبت حضور انجام نشد' in failed.attendance_feedback.text())
            self.assertTrue(failed.worker.isRunning())
            self.assertIn('تشخیص چهره ادامه دارد', failed.attendance_feedback.text())
        finally:
            failed.reject()
            wait_until(lambda: failed.worker is None)
        self.window.people_page.service.archive(person.id)


if __name__ == "__main__":
    unittest.main()
