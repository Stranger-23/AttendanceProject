from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from attendance_app.application.people_service import PeopleService
from attendance_app.configuration.settings import AppConfig
from attendance_app.domain.errors import DuplicatePersonError, PersonNotFoundError, StorageError
from attendance_app.domain.people import PersonInput
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.storage.migrations import apply_migrations, MIGRATIONS
from attendance_app.storage.backup import BackupManager


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = Database(self.directory / 'runtime' / 'smart_attendance.db')
        self.db.initialize()
        self.repo = PeopleRepository(self.db)
        self.service = PeopleService(self.repo)
        self.backup = BackupManager(self.db)

    def add(self, identifier='0012', first='علی', last='احمدی'):
        return self.service.create(PersonInput(first, last, identifier, 'یادداشت'))

    def test_configured_runtime_path(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': str(self.directory)}):
            config = AppConfig()
            self.assertEqual(config.database_path, self.directory / 'SmartAttendance' / 'smart_attendance.db')
            Database(config.database_path).initialize()
            self.assertTrue(config.database_path.is_file())

    def test_fresh_schema_migrations_and_idempotence(self):
        self.db.initialize()
        with self.db.connect() as connection:
            self.assertEqual(connection.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            rows = connection.execute('SELECT version, name, checksum, applied_at FROM schema_migrations').fetchall()
            self.assertEqual(len(rows), 4)
            self.assertEqual(tuple(rows[3][:2]), (4, 'settings'))
            self.assertEqual(tuple(rows[2][:2]), (3, 'attendance'))
            self.assertEqual(tuple(rows[1][:2]), (2, 'face_templates'))
            self.assertEqual(tuple(rows[0][:2]), (1, 'people'))
            self.assertTrue(rows[0][2])
            first_timestamp = rows[0][3]
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {'schema_migrations', 'people', 'face_templates', 'attendance', 'settings', 'sqlite_sequence'})
        self.db.initialize()
        with self.db.connect() as connection:
            self.assertEqual(connection.execute('SELECT applied_at FROM schema_migrations').fetchone()[0], first_timestamp)

    def test_failed_migration_rolls_back_and_order_is_deterministic(self):
        failure = SimpleNamespace(VERSION=2, NAME='broken', STATEMENTS=('CREATE TABLE transient (id INTEGER)', 'INVALID SQL'))
        with closing(sqlite3.connect(':memory:', isolation_level=None)) as connection:
            with self.assertRaises(sqlite3.Error):
                apply_migrations(connection, (failure, MIGRATIONS[0]))
            self.assertEqual(connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])
            apply_migrations(connection)
            self.assertEqual(connection.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 4)

    def test_unknown_migration_fails_without_data_loss(self):
        person = self.add()
        with self.db.connect(write=True) as connection:
            connection.execute("INSERT INTO schema_migrations VALUES (99, 'future', 'unknown', 'now')")
        with self.assertRaises(StorageError):
            self.db.initialize()
        self.assertEqual(self.repo.get(person.id), person)

    def test_create_retrieve_list_and_restart(self):
        person = self.add()
        self.assertEqual(self.repo.get(person.id), person)
        self.assertEqual(self.repo.get_by_person_id('0012'), person)
        self.assertEqual(self.repo.list_active(), [person])
        restarted = Database(self.db.path)
        restarted.initialize()
        self.assertEqual(PeopleRepository(restarted).get(person.id), person)
        with self.db.connect() as connection:
            self.assertEqual(connection.execute('SELECT typeof(person_id) FROM people').fetchone()[0], 'text')

    def test_search_name_id_variations_and_literals(self):
        person = self.add(first='علي', last='كريمي')
        for query in ('علی', 'کریمی', 'علی کریمی', '0012', '012'):
            self.assertEqual(self.repo.search(query), [person])
        self.assertEqual(self.repo.search("' OR 1=1 --"), [])
        self.assertEqual(self.repo.search('%'), [])
        self.assertEqual(self.repo.search('_'), [])
        self.assertEqual(self.repo.search('\\'), [])
        literal = self.add(identifier='A%_01')
        self.assertEqual(self.repo.search('%_'), [literal])

    def test_update_preserves_internal_id_and_registration(self):
        person = self.add()
        changed = self.service.update(person.id, PersonInput('رضا', 'محمدی', '0009'))
        self.assertEqual(changed.id, person.id)
        self.assertEqual(changed.created_at, person.created_at)
        self.assertEqual(changed.person_id, '0009')
        self.assertIsNone(self.repo.get_by_person_id('0012'))
        self.assertEqual(self.repo.get(person.id), changed)

    def test_duplicate_create_and_update_leave_data_unchanged(self):
        first, second = self.add(), self.add('0022')
        with self.assertRaises(DuplicatePersonError):
            self.add()
        with self.assertRaises(DuplicatePersonError):
            self.service.update(second.id, PersonInput('جدید', 'جدید', first.person_id))
        self.assertEqual(self.repo.get(second.id), second)
        self.assertEqual(len(self.repo.list_active()), 2)

    def test_archive_excludes_active_keeps_data_and_reserves_id(self):
        person = self.add()
        self.service.archive(person.id)
        self.assertEqual(self.repo.list_active(), [])
        archived = self.repo.get(person.id)
        self.assertFalse(archived.is_active)
        self.assertEqual(archived.person_id, '0012')
        self.assertEqual(self.repo.search(active=False), [archived])
        with self.assertRaises(DuplicatePersonError):
            self.add()

    def test_missing_person_errors(self):
        with self.assertRaises(PersonNotFoundError):
            self.service.get(999)
        with self.assertRaises(PersonNotFoundError):
            self.service.archive(999)
        with self.assertRaises(PersonNotFoundError):
            self.service.update(999, PersonInput('علی', 'احمدی', '01'))

    def test_transactions_roll_back_and_connections_close(self):
        with self.assertRaises(RuntimeError):
            with self.db.connect(write=True) as connection:
                connection.execute("INSERT INTO people(person_id,first_name,last_name,created_at) VALUES ('x','x','x','now')")
                raise RuntimeError('interrupt')
        self.assertEqual(self.repo.list_active(), [])
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute('SELECT 1')

    def test_backup_restore_and_recovery_copy(self):
        original = self.add()
        path = self.directory / 'backup.db'
        self.backup.backup(path)
        extra = self.add('0022')
        with self.assertRaises(StorageError):
            self.backup.restore(path)
        recovery = self.backup.restore(path, confirmed=True)
        self.assertEqual(self.repo.list_active(), [original])
        self.assertTrue(recovery.is_file())
        self.assertEqual(PeopleRepository(Database(recovery)).get(extra.id), extra)
        self.db.initialize()
        self.assertEqual(PeopleRepository(Database(self.db.path)).list_active(), [original])

    def test_backup_never_overwrites_without_confirmation(self):
        path = self.directory / 'backup.db'
        path.write_bytes(b'existing')
        with self.assertRaises(StorageError):
            self.backup.backup(path)
        self.assertEqual(path.read_bytes(), b'existing')
        self.backup.backup(path, overwrite=True)
        with self.assertRaises(StorageError):
            self.backup.backup(self.db.path, overwrite=True)

    def test_restore_rejects_invalid_and_unrelated_files_without_changes(self):
        person = self.add()
        invalid = self.directory / 'invalid.db'
        invalid.write_bytes(b'not a database')
        unrelated = self.directory / 'unrelated.db'
        with closing(sqlite3.connect(unrelated)) as connection:
            connection.execute('CREATE TABLE unrelated (id INTEGER)')
        for path in (invalid, unrelated, self.directory / 'missing.db', self.db.path):
            with self.subTest(path=path), self.assertRaises(StorageError):
                self.backup.restore(path, confirmed=True)
            self.assertEqual(self.repo.list_active(), [person])

    def test_connection_failure_is_safe_persian_error(self):
        database = Database(self.directory)  # A directory cannot be opened as a database.
        with self.assertRaises(StorageError) as error:
            database.initialize()
        self.assertIn('دسترسی', str(error.exception))
