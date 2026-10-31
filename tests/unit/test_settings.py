from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from attendance_app.application.settings_service import SettingsService
from attendance_app.domain.errors import StorageError, ValidationError
from attendance_app.storage.backup import BackupManager
from attendance_app.storage.database import Database
from attendance_app.storage.migrations import apply_migrations, MIGRATIONS
from attendance_app.storage.repositories.settings import SettingsRepository


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = Database(self.directory / 'app.db')
        self.db.initialize()
        self.repo = SettingsRepository(self.db)
        self.service = SettingsService(self.repo)

    def test_default_does_not_write(self):
        self.assertEqual(self.service.camera_index(), 0)
        self.assertIsNone(self.repo.get('camera_index'))

    def test_save_reload_and_separate_process_restart(self):
        self.service.save_camera_index(16)
        self.assertEqual(SettingsService(SettingsRepository(Database(self.db.path))).camera_index(), 16)
        code = ('from pathlib import Path; '
                'from attendance_app.storage.database import Database; '
                'from attendance_app.storage.repositories.settings import SettingsRepository; '
                'from attendance_app.application.settings_service import SettingsService; '
                'import sys; print(SettingsService(SettingsRepository(Database(Path(sys.argv[1])))).camera_index())')
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.db.path)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), '16')
        self.service.save_camera_index(0)
        self.assertEqual(self.service.camera_index(), 0)

    def test_invalid_inputs_preserve_saved_preference(self):
        self.service.save_camera_index(3)
        for value in (-1, 17, True, False, 1.0, '2', None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.service.save_camera_index(value)
            self.assertEqual(self.service.camera_index(), 3)

    def test_invalid_stored_value_is_reported_without_overwriting(self):
        for value in ('bad', '-1', '17'):
            self.repo.set('camera_index', value)
            with self.assertRaises(StorageError):
                self.service.camera_index()
            self.assertEqual(self.repo.get('camera_index'), value)

    def test_backup_restore_refreshes_existing_service(self):
        self.service.save_camera_index(5)
        backup = self.directory / 'backup.db'
        manager = BackupManager(self.db)
        manager.backup(backup)
        self.service.save_camera_index(9)
        manager.restore(backup, confirmed=True)
        self.assertEqual(self.service.camera_index(), 5)

    def test_v3_upgrade_and_restore_default_preserve_existing_backup(self):
        old = self.directory / 'v3.db'
        with closing(sqlite3.connect(old, isolation_level=None)) as connection:
            apply_migrations(connection, MIGRATIONS[:3])
        original = old.read_bytes()
        self.service.save_camera_index(7)
        BackupManager(self.db).restore(old, confirmed=True)
        self.assertEqual(self.service.camera_index(), 0)
        self.assertEqual(old.read_bytes(), original)
        self.db.initialize()
        self.service.save_camera_index(4)
        self.assertEqual(self.service.camera_index(), 4)
