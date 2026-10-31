from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
import numpy as np

from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.people_service import PeopleService
from attendance_app.domain.errors import ValidationError, StorageError
from attendance_app.domain.face_templates import encode_embedding, decode_embedding
from attendance_app.domain.people import PersonInput
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.storage.backup import BackupManager
from attendance_app.storage.migrations import MIGRATIONS, apply_migrations


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(Path(self.temp.name)/'test.db')
        self.db.initialize()
        self.people = PeopleService(PeopleRepository(self.db))
        self.templates = FaceTemplateRepository(self.db)
        self.service = EnrollmentService(self.people, self.templates)
        self.person = self.people.create(PersonInput('آزمایش', 'نمونه', '0001'))
        # Synthetic vectors test serialization/transactions only, never recognition accuracy.
        self.vectors = [np.eye(128, dtype=np.float32)[i] for i in range(3)]

    def test_numeric_roundtrip_and_invalid_vectors(self):
        payload = encode_embedding(self.vectors[0])
        self.assertEqual(len(payload), 512)
        self.assertEqual(decode_embedding(payload), tuple(self.vectors[0]))
        for values in ([], [0]*128, [float('nan')]*128, [float('inf')]*128):
            with self.assertRaises(ValidationError):
                encode_embedding(values)
        with self.assertRaises(ValidationError):
            decode_embedding(b'wrong')

    def test_save_metadata_and_persistence(self):
        person, ids = self.service.begin(self.person.id)
        self.service.save(person, self.vectors, expected_ids=ids)
        rows = self.templates.list_for_person(person.id)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['dtype'], '<f4')
        self.assertEqual(rows[0]['dimensions'], 128)
        self.assertIn('sface-2021dec:', rows[0]['model_id'])
        self.assertIn('yunet-2026may:', rows[0]['alignment_id'])
        self.assertEqual(FaceTemplateRepository(Database(self.db.path)).list_for_person(person.id), rows)
        with self.db.connect() as c:
            self.assertEqual(c.execute('SELECT typeof(embedding) FROM face_templates').fetchone()[0], 'blob')

    def test_count_confirmation_and_stale_replacement(self):
        with self.assertRaises(ValidationError):
            self.service.save(self.person, self.vectors[:1])
        self.service.save(self.person, self.vectors)
        person, ids = self.service.begin(self.person.id)
        with self.assertRaises(ValidationError):
            self.service.save(person, self.vectors, expected_ids=ids)
        self.service.save(person, self.vectors[::-1], expected_ids=ids, replace_confirmed=True)
        with self.assertRaises(ValidationError):
            self.service.save(person, self.vectors, expected_ids=ids, replace_confirmed=True)

    def test_archive_during_capture_keeps_old_templates(self):
        self.service.save(self.person, self.vectors)
        person, ids = self.service.begin(self.person.id)
        original = self.templates.list_for_person(person.id)
        self.people.archive(person.id)
        with self.assertRaises(ValidationError):
            self.service.begin(person.id)
        with self.assertRaises(ValidationError):
            self.service.save(person, self.vectors, expected_ids=ids, replace_confirmed=True)
        self.assertEqual(self.templates.list_for_person(person.id), original)

    def test_atomic_replacement_rollback_and_foreign_key(self):
        self.service.save(self.person, self.vectors)
        person, ids = self.service.begin(self.person.id)
        original = self.templates.list_for_person(person.id)
        with self.db.connect(write=True) as c:
            c.execute("CREATE TRIGGER test_fail BEFORE INSERT ON face_templates BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(StorageError):
            self.service.save(person, self.vectors, expected_ids=ids, replace_confirmed=True)
        self.assertEqual(self.templates.list_for_person(person.id), original)
        with self.db.connect(write=True) as c:
            c.execute('DROP TRIGGER test_fail')
        with self.assertRaises(StorageError):
            with self.db.connect(write=True) as c:
                c.execute("INSERT INTO face_templates(person_id,embedding,dimensions,dtype,model_id,alignment_id,created_at) VALUES (999,?,128,'<f4','m','a','now')", (encode_embedding(self.vectors[0]),))

    def test_upgrade_v1_preserves_people_and_restores_v1_backup(self):
        old = Path(self.temp.name)/'v1.db'
        with closing(sqlite3.connect(old, isolation_level=None)) as c:
            apply_migrations(c, MIGRATIONS[:1])
            c.execute("INSERT INTO people(person_id,first_name,last_name,created_at) VALUES ('0012','old','person','2026-01-01T00:00:00+00:00')")
        upgraded = Database(old)
        upgraded.initialize()
        upgraded.initialize()
        self.assertEqual(PeopleRepository(upgraded).get_by_person_id('0012').first_name, 'old')
        # A genuinely old backup remains unchanged; only its private restore snapshot migrates.
        backup_v1 = Path(self.temp.name)/'backup-v1.db'
        with closing(sqlite3.connect(backup_v1, isolation_level=None)) as c:
            apply_migrations(c, MIGRATIONS[:1])
        BackupManager(self.db).restore(backup_v1, confirmed=True)
        with self.db.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 4)
        with closing(sqlite3.connect(backup_v1)) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 1)

    def test_backup_roundtrip_with_templates(self):
        self.service.save(self.person, self.vectors)
        original = self.templates.list_for_person(self.person.id)
        path = Path(self.temp.name)/'backup.db'
        backup = BackupManager(self.db)
        backup.backup(path)
        person, ids = self.service.begin(self.person.id)
        self.service.save(person, self.vectors[::-1], expected_ids=ids, replace_confirmed=True)
        backup.restore(path, confirmed=True)
        self.assertEqual(self.templates.list_for_person(person.id), original)
