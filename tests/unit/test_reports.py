from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.report_service import ReportService
from attendance_app.domain.errors import ValidationError
from attendance_app.domain.people import PersonInput
from attendance_app.domain.reports import ReportFilters
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.people import PeopleRepository


class ReportsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(Path(self.temp.name) / 'report.db')
        self.db.initialize()
        self.people = PeopleRepository(self.db)
        self.a = self.people.create(PersonInput('علي', 'كریمی', '0001'))
        self.b = self.people.create(PersonInput('دیگر', 'فرد', 'A%_\\01'))
        with self.db.connect(write=True) as connection:
            for person, day in ((self.a, '2026-10-26'), (self.a, '2026-10-27'), (self.b, '2026-10-27')):
                connection.execute('''INSERT INTO attendance
                    (person_id,attendance_date,attendance_time,observed_at,created_at)
                    VALUES (?,?,'23:59:59-04:00',?,?)''',
                    (person.id, day, day + 'T00:00:00+00:00', day + 'T00:00:00+00:00'))
        self.attendance = AttendanceService(AttendanceRepository(self.db))
        self.service = ReportService(self.attendance)

    def test_filters_summaries_and_history_agree(self):
        for filters in (ReportFilters(), ReportFilters(status='present'), ReportFilters(query='علی'),
                        ReportFilters(query='%_\\'), ReportFilters(person_id=self.a.id,
                        start_date='2026-10-27', end_date='2026-10-27')):
            snapshot, _ = self.service.read(filters)
            expected = self.attendance.search_history(filters.query, person_id=filters.person_id,
                start_date=filters.start_date, end_date=filters.end_date)
            self.assertEqual(snapshot.records, tuple(expected))
            self.assertEqual(snapshot.record_count, len(expected))
            self.assertEqual(snapshot.people_count, len({r.person_id for r in expected}))
        self.assertEqual(self.service.read(ReportFilters())[0].record_count, 3)
        self.assertEqual(self.service.read(ReportFilters())[0].people_count, 2)

    def test_archive_current_identity_and_immutable_snapshot(self):
        snapshot, _ = self.service.read(ReportFilters(person_id=self.a.id))
        self.people.update(self.a.id, PersonInput('نام', 'جدید', '0009'))
        self.people.archive(self.a.id)
        fresh, people = self.service.read(snapshot.filters)
        self.assertTrue(all(r.public_person_id == '0009' and not r.is_active for r in fresh.records))
        self.assertTrue(all(r.public_person_id == '0001' for r in snapshot.records))
        self.assertIn(self.a.id, [p.id for p in people])
        with self.assertRaises(FrozenInstanceError):
            snapshot.records = ()

    def test_invalid_empty_and_readonly(self):
        with self.db.connect() as connection:
            before = tuple(connection.iterdump())
        for filters in (ReportFilters(status='absent'), ReportFilters(start_date='bad'),
                        ReportFilters(start_date='2026-10-28', end_date='2026-10-27')):
            with self.assertRaises(ValidationError):
                self.service.read(filters)
        snapshot, _ = self.service.read(ReportFilters(start_date='2099-01-01'))
        self.assertEqual((snapshot.record_count, snapshot.people_count), (0, 0))
        with self.db.connect() as connection:
            self.assertEqual(tuple(connection.iterdump()), before)
