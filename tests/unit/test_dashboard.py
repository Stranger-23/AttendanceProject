from contextlib import closing, contextmanager
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter
import unittest
from unittest.mock import patch

import numpy as np
from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.people_service import PeopleService
from attendance_app.domain.errors import StorageError, ValidationError
from attendance_app.domain.people import PersonInput
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.storage.repositories.people import PeopleRepository


class DashboardTests(unittest.TestCase):
    DAY = '2026-10-27'

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Database(Path(temp.name) / 'dashboard.db')
        self.db.initialize()
        self.people = PeopleRepository(self.db)
        self.repo = AttendanceRepository(self.db)
        self.service = AttendanceService(self.repo)

    def person(self, identifier):
        return self.people.create(PersonInput('نام', 'نمونه', identifier))

    def insert(self, person, day=DAY, clock='08:30:00+03:30'):
        with self.db.connect(write=True) as connection:
            connection.execute('''INSERT INTO attendance
                (person_id,attendance_date,attendance_time,observed_at,status,created_at)
                VALUES (?,?,?,?,'present',?)''',
                (person.id, day, clock, day + 'T05:00:00+00:00', day + 'T05:00:01+00:00'))

    def snapshot(self, day=DAY):
        return self.service.get_dashboard_snapshot(day)

    def test_empty_people_only_and_invalid_day(self):
        snapshot = self.snapshot()
        self.assertEqual((snapshot.registered_people, snapshot.active_people,
                          snapshot.today_attendance, snapshot.total_attendance), (0, 0, 0, 0))
        self.assertEqual(snapshot.recent, ())
        self.person('0001')  # No face enrollment, still an active person.
        snapshot = self.snapshot()
        self.assertEqual((snapshot.registered_people, snapshot.active_people,
                          snapshot.today_attendance, snapshot.total_attendance), (1, 1, 0, 0))
        for invalid in (None, '', '2026-2-01', '2026-02-30', '1405/08/05', 1, '20261027'):
            with self.assertRaises(ValidationError):
                self.snapshot(invalid)

    def test_population_counts_current_identity_and_all_archived(self):
        a, b, c = [self.person(identifier) for identifier in ('0001', '0002', '0003')]
        self.insert(a, '2026-10-26')
        self.insert(a)
        self.insert(c)
        self.people.archive(c.id)
        self.people.update(c.id, PersonInput('نام جدید', 'بایگانی', '0009'))
        snapshot = self.snapshot()
        self.assertEqual((snapshot.registered_people, snapshot.active_people,
                          snapshot.today_attendance, snapshot.total_attendance), (3, 2, 2, 3))
        self.assertEqual(snapshot.recent[0].public_person_id, '0009')
        self.assertEqual(snapshot.recent[0].full_name, 'نام جدید بایگانی')
        self.assertFalse(snapshot.recent[0].is_active)
        self.assertEqual(snapshot.today_attendance,
                         len(self.service.search_history(start_date=self.DAY, end_date=self.DAY)))
        self.people.archive(a.id)
        self.people.archive(b.id)
        snapshot = self.snapshot()
        self.assertEqual((snapshot.registered_people, snapshot.active_people,
                          snapshot.today_attendance, snapshot.total_attendance), (3, 0, 2, 3))
        with self.assertRaises(FrozenInstanceError):
            snapshot.today_attendance = 42
        self.assertIsInstance(snapshot.recent, tuple)

    def test_local_day_is_stored_day_offsets_and_future_rows_remain(self):
        a, b = self.person('01'), self.person('02')
        self.insert(a, clock='00:01:00+14:00')
        self.insert(b, '2026-10-26', '23:59:00-12:00')
        self.assertEqual(self.snapshot().today_attendance, 1)
        self.assertEqual(self.snapshot('2026-10-28').today_attendance, 0)
        self.assertEqual(self.snapshot('2026-10-28').total_attendance, 2)
        self.insert(a, '2027-01-01')
        self.assertEqual(self.snapshot().recent[0].attendance_date, '2027-01-01')

    def test_recent_exact_limit_ties_and_history_order(self):
        for number in range(12):
            self.insert(self.person(f'{number:04}'))
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot.recent), 10)
        self.assertEqual(snapshot.recent, tuple(self.service.search_history()[:10]))
        self.assertEqual([r.id for r in snapshot.recent], list(range(12, 2, -1)))
        self.assertEqual(snapshot.total_attendance, 12)

    def test_repeated_record_keeps_counts_and_first_time(self):
        person = self.person('0001')
        EnrollmentService(PeopleService(self.people), FaceTemplateRepository(self.db)).save(
            person, [np.eye(128)[0]] * 3)
        observed = datetime(2026, 10, 27, 8, 30, tzinfo=timezone(timedelta(hours=3, minutes=30)))
        first = self.repo.record(person.id, observed, .8)
        repeated = self.repo.record(person.id, observed + timedelta(hours=1), .9)
        self.assertFalse(repeated.created)
        snapshot = self.snapshot()
        self.assertEqual((snapshot.today_attendance, snapshot.total_attendance), (1, 1))
        self.assertEqual(snapshot.recent[0].attendance_time, first.attendance_time)

    def test_read_only_transaction_trace_dump_and_failure(self):
        self.insert(self.person('01'))
        with self.db.connect() as connection:
            before = '\n'.join(connection.iterdump())
        statements = []
        connect = self.db.connect
        @contextmanager
        def traced(*, write=False):
            self.assertFalse(write)
            with connect() as connection:
                connection.execute('PRAGMA query_only=ON')
                connection.set_trace_callback(statements.append)
                yield connection
        with patch.object(self.db, 'connect', traced):
            self.snapshot()
        self.assertEqual(statements[0], 'BEGIN')
        self.assertEqual(statements[-1], 'COMMIT')
        self.assertEqual(sum(sql.lstrip().startswith('SELECT') for sql in statements), 2)
        self.assertFalse(any('IMMEDIATE' in sql for sql in statements))
        with self.db.connect() as connection:
            self.assertEqual('\n'.join(connection.iterdump()), before)
        with patch.object(self.db, 'connect', side_effect=StorageError()):
            with self.assertRaises(StorageError):
                self.snapshot()

    def test_one_snapshot_even_when_external_writer_commits_between_queries(self):
        person = self.person('01')
        self.insert(person)
        # WAL is test-only, allowing an independent commit while the reader holds its snapshot.
        with closing(sqlite3.connect(self.db.path)) as connection:
            connection.execute('PRAGMA journal_mode=WAL')
        connect = self.db.connect
        writes = []
        def interleave(sql):
            if 'FROM attendance a JOIN people p' in sql and not writes:
                with closing(sqlite3.connect(self.db.path)) as writer:
                    writer.execute("INSERT INTO people(person_id,first_name,last_name,created_at) VALUES ('02','new','person','2026-10-27T00:00:00+00:00')")
                    writer.execute('''INSERT INTO attendance
                        (person_id,attendance_date,attendance_time,observed_at,status,created_at)
                        SELECT last_insert_rowid(), attendance_date, attendance_time, observed_at, status, created_at
                        FROM attendance LIMIT 1''')
                    writer.commit()
                writes.append(True)
        @contextmanager
        def traced(*, write=False):
            with connect(write=write) as connection:
                connection.set_trace_callback(interleave)
                yield connection
        with patch.object(self.db, 'connect', traced):
            snapshot = self.snapshot()
        self.assertEqual(writes, [True])
        self.assertEqual((snapshot.registered_people, snapshot.today_attendance, len(snapshot.recent)), (1, 1, 1))
        self.assertEqual(self.snapshot().total_attendance, 2)

    def test_multi_thousand_row_snapshot_without_new_index(self):
        person = self.person('01')
        rows = [(person.id, (date(2000, 1, 1) + timedelta(days=offset)).isoformat()) for offset in range(5000)]
        with self.db.connect(write=True) as connection:
            indexes_before = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='index'").fetchall()
            connection.executemany('''INSERT INTO attendance
                (person_id,attendance_date,attendance_time,observed_at,status,created_at)
                VALUES (?,?,'08:00:00+03:30','2000-01-01T04:30:00+00:00','present','2000-01-01T04:30:00+00:00')''', rows)
        started = perf_counter()
        snapshot = self.snapshot()
        self.assertEqual(snapshot.total_attendance, 5000)
        self.assertEqual(len(snapshot.recent), 10)
        self.elapsed = perf_counter() - started
        with self.db.connect() as connection:
            self.assertEqual(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='index'").fetchall(), indexes_before)


if __name__ == '__main__':
    unittest.main()
