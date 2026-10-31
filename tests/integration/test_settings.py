from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from attendance_app.application.settings_service import SettingsService
from attendance_app.application.storage_service import StorageService
from attendance_app.storage.backup import BackupManager
from attendance_app.domain.errors import StorageError
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.settings import SettingsRepository
from attendance_app.ui.pages.storage_settings import StorageSettingsPage
from attendance_app.ui.pages.recognition import RecognitionPage
from attendance_app.ui.pages.people import PeoplePage
from attendance_app.ui.dialogs.enrollment import FaceCaptureDialog
from attendance_app.ui.dialogs.recognition import RecognitionDialog


class FakeWorker(QObject):
    sample_ready = Signal(object)
    sample_rejected = Signal(str)
    failed = Signal(str)
    finished = Signal()
    attendance_status = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.index = args[2]

    def start(self):
        self.failed.emit('دوربین باز نشد.')
        self.finished.emit()


class SettingsUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owns_app = QApplication.instance() is None
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        if cls.owns_app:
            import shiboken6
            shiboken6.delete(cls.app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(Path(self.temp.name) / 'app.db')
        self.db.initialize()
        self.service = SettingsService(SettingsRepository(self.db))

    def test_settings_save_error_refresh_and_about(self):
        page = StorageSettingsPage(Mock(), settings_service=self.service)
        self.addCleanup(page.close)
        self.assertEqual(page.camera_index.value(), 0)
        page.camera_index.setValue(6)
        page.save_camera_button.click()
        self.assertEqual(self.service.camera_index(), 6)
        self.assertIn('ذخیره شد', page.camera_feedback.text())
        with patch.object(self.service, 'save_camera_index', side_effect=StorageError()):
            page.save_camera_button.click()
        self.assertIn('خطا', page.camera_feedback.text())
        self.service.save_camera_index(2)
        page.restored.emit()
        self.assertEqual(page.camera_index.value(), 2)
        self.assertIn('0.1.0', page.about.text())
        self.assertTrue(page.backup_button.isEnabled())

    def test_recognition_page_reads_saved_default_each_open_and_reports_errors(self):
        page = RecognitionPage(Path('.'), Mock(), settings_service=self.service)
        self.addCleanup(page.close)
        with patch('attendance_app.ui.pages.recognition.RecognitionDialog') as dialog:
            page.open_camera()
            self.assertEqual(dialog.call_args.kwargs['camera_index'], 0)
            self.service.save_camera_index(8)
            page.open_camera()
            self.assertEqual(dialog.call_args.kwargs['camera_index'], 8)
            with patch.object(self.service, 'camera_index', side_effect=StorageError()):
                page.open_camera()
            self.assertIn('خطا', page.feedback.text())

    def test_enrollment_page_uses_saved_default(self):
        self.service.save_camera_index(4)
        enrollment = Mock()
        person = SimpleNamespace(id=1)
        enrollment.begin.return_value = (person, ())
        page = PeoplePage(Mock(), enrollment_service=enrollment, model_dir=Path('.'),
                          settings_service=self.service)
        self.addCleanup(page.close)
        page.with_selected = lambda action: action(person)
        with patch('attendance_app.ui.pages.people.FaceCaptureDialog') as dialog:
            page.open_enrollment()
            self.assertEqual(dialog.call_args.kwargs['camera_index'], 4)

    def test_real_restore_refreshes_control_and_next_camera(self):
        manager = BackupManager(self.db)
        backup = Path(self.temp.name) / 'backup.db'
        self.service.save_camera_index(3)
        manager.backup(backup)
        self.service.save_camera_index(11)
        page = StorageSettingsPage(StorageService(manager), settings_service=self.service)
        self.addCleanup(page.close)
        restored = Mock()
        page.restored.connect(restored)
        with patch('attendance_app.ui.pages.storage_settings.QFileDialog.getOpenFileName',
                   return_value=(str(backup), '')), \
             patch('attendance_app.ui.pages.storage_settings.confirm', return_value=True):
            page.restore()
        self.assertEqual(page.camera_index.value(), 3)
        self.assertEqual(restored.call_count, 1)
        recognition = RecognitionPage(Path('.'), Mock(), settings_service=self.service)
        self.addCleanup(recognition.close)
        with patch('attendance_app.ui.pages.recognition.RecognitionDialog') as dialog:
            recognition.open_camera()
            self.assertEqual(dialog.call_args.kwargs['camera_index'], 3)

    def test_open_dialog_keeps_index_and_workers_receive_it_on_unavailable_camera(self):
        for kind in (FaceCaptureDialog, RecognitionDialog):
            with self.subTest(dialog=kind.__name__):
                self.service.save_camera_index(7)
                options = dict(camera_index=self.service.camera_index(), worker_factory=FakeWorker)
                dialog = (kind(Path('.'), Mock(), **options) if kind is RecognitionDialog
                          else kind(Path('.'), **options))
                self.service.save_camera_index(9)
                self.assertEqual(dialog.camera_index.value(), 7)
                with patch.object(FakeWorker, 'start') as start:
                    dialog.start_camera()
                    self.assertEqual(dialog.worker.index, 7)
                    self.assertTrue(start.called)
                    dialog.worker.failed.emit('دوربین باز نشد.')
                    dialog.worker.finished.emit()
                self.assertIsNone(dialog.worker)
                self.assertIn('دوربین باز نشد', dialog.status.text())
                self.assertTrue(dialog.start_button.isEnabled())
                self.assertEqual(self.service.camera_index(), 9)
                dialog.close()
