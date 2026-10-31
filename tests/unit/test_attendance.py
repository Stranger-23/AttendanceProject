from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import Mock

import numpy as np

from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.attendance_recorder import AttendanceRecorder
from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.people_service import PeopleService
from attendance_app.domain.errors import StorageError, ValidationError
from attendance_app.domain.people import PersonInput
from attendance_app.recognition.engine import Analysis
from attendance_app.recognition.matching import RecognitionEngine, RecognitionResult
from attendance_app.recognition.worker import RecognitionWorker
from attendance_app.storage.backup import BackupManager
from attendance_app.storage.database import Database
from attendance_app.storage.migrations import MIGRATIONS, apply_migrations
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.storage.repositories.people import PeopleRepository


class AttendanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(Path(self.temp.name) / 'test.db')
        self.db.initialize()
        self.people = PeopleService(PeopleRepository(self.db))
        self.templates = FaceTemplateRepository(self.db)
        self.repo = AttendanceRepository(self.db)
        self.service = AttendanceService(self.repo)
        self.person = self.enroll('001', 0)
        self.observed = datetime(2026, 10, 24, 23, 59, 59, 123456,
                                 tzinfo=timezone(timedelta(hours=3, minutes=30)))

    def enroll(self, identifier, vector):
        person = self.people.create(PersonInput('حسین', 'افشار', identifier))
        EnrollmentService(self.people, self.templates).save(person, [np.eye(128)[vector]] * 3)
        return person

    def result(self, person=None):
        person = person or self.person
        return RecognitionResult((0, 0, 100, 100), 'known', person.id, person.full_name, .8)

    def rows(self):
        with self.db.connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM attendance ORDER BY id')]

    def analysis(self, vector=0, x=0):
        face = np.zeros((1, 15), np.float32)
        face[0, :4] = [x, 0, 100, 100]
        return Analysis(face, 'ready', '', 0, embedding=np.eye(128)[vector])

    def test_only_confirmed_known_creates_record_after_three_frames(self):
        matcher = RecognitionEngine(self.templates.list_active())
        for _ in range(2):
            result = matcher.recognize([self.analysis()])[0]
            self.assertIsNone(self.service.record(result, self.observed))
            self.assertEqual(self.rows(), [])
        receipt = self.service.record(matcher.recognize([self.analysis()])[0], self.observed)
        self.assertTrue(receipt.created)
        self.assertEqual(receipt.person_id, self.person.id)
        self.assertEqual(receipt.status, 'present')
        self.assertEqual(receipt.attendance_date, '2026-10-24')
        self.assertEqual(receipt.attendance_time, '23:59:59+03:30')
        self.assertEqual(datetime.fromisoformat(receipt.observed_at), self.observed)
        self.assertEqual(len(self.rows()), 1)

    def test_repeated_frames_restart_preserve_first_observation(self):
        first = self.service.record(self.result(), self.observed)
        restarted = AttendanceService(AttendanceRepository(Database(self.db.path)))
        for _ in range(100):
            receipt = restarted.record(self.result(), self.observed + timedelta(microseconds=100))
            self.assertFalse(receipt.created)
            self.assertEqual(receipt.id, first.id)
            self.assertEqual(receipt.observed_at, first.observed_at)
        self.assertEqual(len(self.rows()), 1)

    def test_unknown_and_empty_frames_never_write_even_with_identity_field(self):
        unknown = RecognitionResult((0, 0, 100, 100), 'unknown', self.person.id, 'ignored', .9)
        self.assertIsNone(self.service.record(unknown, self.observed))
        matcher = RecognitionEngine(self.templates.list_active())
        self.assertEqual(matcher.recognize([]), [])
        for _ in range(4):
            for result in matcher.recognize([self.analysis(1)]):
                self.assertIsNone(self.service.record(result, self.observed))
        self.assertEqual(self.rows(), [])

    def test_two_known_people_each_receive_one_record(self):
        other = self.enroll('002', 1)
        matcher = RecognitionEngine(self.templates.list_active())
        for _ in range(20):
            for result in matcher.recognize([self.analysis(), self.analysis(1, 200)]):
                self.service.record(result, self.observed)
        self.assertEqual({row['person_id'] for row in self.rows()}, {self.person.id, other.id})
        self.assertEqual(len(self.rows()), 2)

    def test_known_unknown_pair_records_only_known(self):
        matcher = RecognitionEngine(self.templates.list_active())
        for _ in range(20):
            for result in matcher.recognize([self.analysis(), self.analysis(1, 200)]):
                self.service.record(result, self.observed)
        self.assertEqual([row['person_id'] for row in self.rows()], [self.person.id])

    def test_database_uniqueness_and_independent_connection_race(self):
        def record(_):
            return AttendanceRepository(Database(self.db.path)).record(self.person.id, self.observed, .8)
        with ThreadPoolExecutor(max_workers=6) as pool:
            receipts = list(pool.map(record, range(12)))
        self.assertEqual(sum(receipt.created for receipt in receipts), 1)
        with self.assertRaises(StorageError):
            with self.db.connect(write=True) as connection:
                connection.execute('''INSERT INTO attendance
                    (person_id,attendance_date,attendance_time,observed_at,status,similarity,created_at)
                    SELECT person_id,attendance_date,attendance_time,observed_at,status,similarity,created_at
                    FROM attendance''')
        self.assertEqual(len(self.rows()), 1)

    def test_local_midnight_allows_next_day_and_writer_cache_rolls_over(self):
        messages = []
        recorder = AttendanceRecorder(self.service, messages.append)
        try:
            recorder.submit([self.result()], self.observed)
            recorder.queue.join()
            tomorrow = self.observed + timedelta(seconds=1)
            recorder.submit([self.result()], tomorrow)
            recorder.queue.join()
        finally:
            recorder.close()
        self.assertEqual([row['attendance_date'] for row in self.rows()], ['2026-10-24', '2026-10-25'])
        self.assertEqual(len(messages), 2)

    def test_invalid_time_score_and_inactive_or_unenrolled_person_rejected(self):
        for observed, score in ((datetime.now(), .8), (self.observed, float('nan')), (self.observed, 2)):
            with self.assertRaises(ValidationError):
                self.repo.record(self.person.id, observed, score)
        unenrolled = self.people.create(PersonInput('نام', 'نمونه', '003'))
        with self.assertRaises(ValidationError):
            self.service.record(self.result(unenrolled), self.observed)
        self.people.archive(self.person.id)
        with self.assertRaises(ValidationError):
            self.service.record(self.result(), self.observed)
        self.assertEqual(self.rows(), [])

    def test_failed_transaction_rolls_back_and_retries_without_false_success(self):
        with self.db.connect(write=True) as connection:
            connection.execute("CREATE TRIGGER fail_attendance AFTER INSERT ON attendance BEGIN SELECT RAISE(ABORT, 'failure'); END")
        messages, ticks = [], [0]
        recorder = AttendanceRecorder(self.service, messages.append, clock=lambda: ticks[0])
        try:
            recorder.submit([self.result()], self.observed)
            recorder.queue.join()
            self.assertEqual(self.rows(), [])
            self.assertIn('ثبت حضور انجام نشد', messages[0])
            recorder.submit([self.result()], self.observed)
            recorder.queue.join()
            self.assertEqual(len(messages), 1)  # Failure backoff avoids frame-by-frame spam.
            with self.db.connect(write=True) as connection:
                connection.execute('DROP TRIGGER fail_attendance')
            ticks[0] = 4
            recorder.submit([self.result()], self.observed)
            recorder.queue.join()
            self.assertIn('ثبت شد', messages[-1])
            for _ in range(100):
                recorder.submit([self.result()], self.observed)
            recorder.queue.join()
            self.assertEqual(len(messages), 2)
        finally:
            recorder.close()
        self.assertEqual(len(self.rows()), 1)

    def test_background_queue_coalesces_and_does_not_block_recognition(self):
        entered, release = Event(), Event()
        real_record = self.service.record
        def slow(result, observed):
            entered.set()
            if not release.wait(3):
                raise RuntimeError('Test writer not released')
            return real_record(result, observed)
        service = Mock()
        service.record.side_effect = slow
        messages = []
        recorder = AttendanceRecorder(service, messages.append, capacity=1)
        try:
            recorder.submit([self.result()], self.observed)
            self.assertTrue(entered.wait(2))
            for _ in range(100):
                recorder.submit([self.result()], self.observed)
            self.assertEqual(recorder.queue.qsize(), 0)
            self.assertEqual(messages, [])  # No notification before commit.
        finally:
            release.set()
            recorder.close()
        self.assertEqual(service.record.call_count, 1)
        self.assertEqual(len(messages), 1)
        # A new session reports an existing record once, not a new success.
        recorder = AttendanceRecorder(self.service, messages.append)
        recorder.submit([self.result()], self.observed)
        recorder.close()
        self.assertIn('قبلاً', messages[-1])

    def test_worker_integrates_confirmed_output_and_survives_database_failure(self):
        service = Mock()
        service.record.side_effect = StorageError()
        worker = None
        frames, released = [], []
        tests = self
        class Camera:
            def __init__(self, *_): pass
            def __enter__(self): return self
            def __exit__(self, *_): released.append(True)
            def read(self):
                frames.append(True)
                return np.zeros((240, 320, 3), np.uint8)
        class Engine:
            def __init__(self, *_): pass
            def analyze_all(self, _): return [tests.analysis(), tests.analysis(1, 200)]
        worker = RecognitionWorker('.', self.templates, engine_factory=Engine, camera_factory=Camera,
                                   attendance_service=service)
        worker.isInterruptionRequested = lambda: len(frames) >= 12
        failures = []
        worker.failed.connect(failures.append)
        worker.run()
        self.assertEqual(len(frames), 12)
        self.assertEqual(failures, [])
        self.assertTrue(released)
        self.assertGreaterEqual(service.record.call_count, 1)
        self.assertTrue(all(call.args[0].state == 'known' for call in service.record.call_args_list))
        self.assertEqual(self.rows(), [])

    def test_upgrade_v2_backup_roundtrip_and_older_backup_preservation(self):
        old = Path(self.temp.name) / 'v2.db'
        with closing(sqlite3.connect(old, isolation_level=None)) as connection:
            apply_migrations(connection, MIGRATIONS[:2])
            connection.execute("INSERT INTO people(person_id,first_name,last_name,created_at) VALUES ('old','old','person','2026-01-01T00:00:00+00:00')")
        upgraded = Database(old)
        upgraded.initialize()
        self.assertIsNotNone(PeopleRepository(upgraded).get_by_person_id('old'))
        receipt = self.service.record(self.result(), self.observed)
        backup = BackupManager(self.db)
        path = Path(self.temp.name) / 'backup.db'
        backup.backup(path)
        self.service.record(self.result(), self.observed + timedelta(days=1))
        recovery = backup.restore(path, confirmed=True)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]['id'], receipt.id)
        with Database(recovery).connect() as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM attendance').fetchone()[0], 2)
        v2 = Path(self.temp.name) / 'backup-v2.db'
        with closing(sqlite3.connect(v2, isolation_level=None)) as connection:
            apply_migrations(connection, MIGRATIONS[:2])
        backup.restore(v2, confirmed=True)
        self.assertEqual(self.rows(), [])
        with closing(sqlite3.connect(v2)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 2)

    def test_commit_failure_returns_no_success_receipt(self):
        @contextmanager
        def fail_commit(*, write=False):
            with self.db.connect(write=write) as connection:
                yield connection
                raise StorageError('خطای آزمایشی هنگام نهایی‌سازی تراکنش')
        database = Mock()
        database.connect = fail_commit
        with self.assertRaises(StorageError):
            AttendanceRepository(database).record(self.person.id, self.observed, .8)
        self.assertEqual(self.rows(), [])

    def test_queue_overflow_reports_unsaved_observation_and_other_people_continue(self):
        second, third = self.enroll('002', 1), self.enroll('003', 2)
        entered, release = Event(), Event()
        real_record = self.service.record
        def slow(result, observed):
            if result.person_id == self.person.id:
                entered.set()
                if not release.wait(3):
                    raise RuntimeError('Test writer not released')
            return real_record(result, observed)
        service, messages = Mock(), []
        service.record.side_effect = slow
        recorder = AttendanceRecorder(service, messages.append, capacity=1)
        try:
            recorder.submit([self.result()], self.observed)
            self.assertTrue(entered.wait(2))
            recorder.submit([self.result(second)], self.observed)
            recorder.submit([self.result(third)], self.observed)
            self.assertIn('هنوز انجام نشده', messages[0])
            release.set()
            recorder.queue.join()
            recorder.submit([self.result(third)], self.observed)
            recorder.queue.join()
        finally:
            release.set()
            recorder.close()
        self.assertEqual(len(self.rows()), 3)
