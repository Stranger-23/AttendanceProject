from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from attendance_app.application.attendance_service import AttendanceService
from attendance_app.domain.errors import StorageError, ValidationError
from attendance_app.domain.people import PersonInput
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.attendance import AttendanceRepository
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.ui.formatting import PERSIAN_CALENDAR, attendance_date, canonical_date
from attendance_app.ui.table_models.attendance import AttendanceTableModel


class HistoryTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Database(Path(temp.name) / 'history.db')
        self.db.initialize()
        self.people = PeopleRepository(self.db)
        self.person = self.people.create(PersonInput('علي', 'كريمي', 'Ab0012'))
        self.other = self.people.create(PersonInput('مریم', 'احمدی', 'A%_\\01'))
        self.unrecorded = self.people.create(PersonInput('بدون', 'حضور', '003'))
        self.repo = AttendanceRepository(self.db)
        self.service = AttendanceService(self.repo)
        for person, day, clock in ((self.person, '2026-10-27', '08:30:00'),
                                   (self.person, '2026-10-28', '09:10:00'),
                                   (self.other, '2026-10-28', '09:10:00')):
            with self.db.connect(write=True) as connection:
                connection.execute('''INSERT INTO attendance
                    (person_id,attendance_date,attendance_time,observed_at,status,similarity,created_at)
                    VALUES (?,?,?,?,'present',NULL,?)''',
                    (person.id, day, clock + '+03:30', day + 'T05:00:00+00:00', day + 'T05:01:00+00:00'))

    def test_empty_search_and_deterministic_order(self):
        rows = self.service.search_history()
        self.assertEqual([r.person_id for r in rows], [self.other.id, self.person.id, self.person.id])
        self.assertEqual(rows[-1].public_person_id, 'Ab0012')
        self.assertEqual(self.service.search_history('   \t'), rows)
        self.assertEqual([p.id for p in self.service.list_history_people()], [self.other.id, self.person.id])

    def test_existing_normalization_and_literal_substrings(self):
        for query in ('علی', 'کریمی', '  علی   کریمی ', 'ab0012', '0012'):
            self.assertEqual(len(self.service.search_history(query)), 2)
        for query in ('%', '_', '\\', '%_\\'):
            self.assertEqual([r.person_id for r in self.service.search_history(query)], [self.other.id])
        for query in ("' OR 1=1 --", 'علی\u200cکریمی', 'ab۰۰۱۲'):
            self.assertEqual(self.service.search_history(query), [])

    def test_inclusive_dates_and_combined_filters(self):
        self.assertEqual(len(self.service.search_history(start_date='2026-10-27', end_date='2026-10-28')), 3)
        self.assertEqual(len(self.service.search_history(start_date='2026-10-28', end_date='2026-10-28')), 2)
        self.assertEqual(len(self.service.search_history('علی', person_id=self.person.id,
                                                       start_date='2026-10-28', end_date='2026-10-28')), 1)
        self.assertEqual(self.service.search_history('علی', person_id=self.other.id), [])
        for day in ('2026-10-26', '2099-01-01'):
            self.assertEqual(self.service.search_history(start_date=day, end_date=day), [])

    def test_invalid_filters(self):
        for filters in ({'start_date': '2026-2-01'}, {'start_date': '2026-02-30'},
                        {'end_date': 12}, {'start_date': '20261027'}, {'person_id': True},
                        {'person_id': 0}, {'query': None},
                        {'start_date': '2026-10-28', 'end_date': '2026-10-27'}):
            with self.assertRaises(ValidationError):
                self.service.search_history(**filters)

    def test_current_identity_and_archive_without_enrollment(self):
        self.people.update(self.person.id, PersonInput('نام', 'جدید', '0009'))
        self.people.archive(self.person.id)
        rows = self.service.search_history(person_id=self.person.id)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.full_name == 'نام جدید' and r.public_person_id == '0009' and not r.is_active for r in rows))
        self.assertIn(self.person.id, [p.id for p in self.service.list_history_people()])

    def test_reads_do_not_write_and_failures_propagate(self):
        with self.db.connect() as connection:
            before = '\n'.join(connection.iterdump())
        self.service.search_history()
        self.service.list_history_people()
        with self.db.connect() as connection:
            self.assertEqual('\n'.join(connection.iterdump()), before)
        with patch.object(self.db, 'connect', side_effect=StorageError()):
            with self.assertRaises(StorageError):
                self.service.search_history()

    def test_solar_hijri_known_dates_leap_and_roundtrip(self):
        for iso, solar in (('2026-10-27', '1405/08/05'), ('2021-03-20', '1399/12/30'),
                           ('2021-03-21', '1400/01/01'), ('2025-03-20', '1403/12/30'),
                           ('2025-03-21', '1404/01/01')):
            self.assertEqual(attendance_date(iso), solar)
            self.assertEqual(canonical_date(QDate(*map(int, solar.split('/')), PERSIAN_CALENDAR)), iso)
        self.assertFalse(QDate(1400, 12, 30, PERSIAN_CALENDAR).isValid())
        with self.assertRaises(ValueError):
            attendance_date('invalid')

    def test_model_display_and_sorting_without_timezone_conversion(self):
        model = AttendanceTableModel()
        model.replace(self.service.search_history())
        self.assertEqual(model.data(model.index(2, 2)), '1405/08/05')
        self.assertEqual(model.data(model.index(2, 3)), '08:30:00')
        self.assertEqual(model.data(model.index(2, 4)), 'حاضر')
        model.sort(2, Qt.SortOrder.AscendingOrder)
        self.assertEqual(model.records[0].attendance_date, '2026-10-27')
        model.sort(1, Qt.SortOrder.AscendingOrder)
        self.assertEqual(model.records[0].public_person_id, 'A%_\\01')

    def test_multi_thousand_rows_are_not_silently_limited(self):
        rows = []
        for offset in range(5000):
            day = (date(2000, 1, 1) + timedelta(days=offset)).isoformat()
            rows.append((self.person.id, day, day + 'T05:00:00+00:00', day + 'T05:00:01+00:00'))
        with self.db.connect(write=True) as connection:
            connection.executemany('''INSERT INTO attendance
                (person_id,attendance_date,attendance_time,observed_at,status,created_at)
                VALUES (?,?,'08:30:00+03:30',?,'present',?)''', rows)
        results = self.service.search_history()
        self.assertEqual(len(results), 5003)
        model = AttendanceTableModel()
        model.replace(results)
        self.assertEqual(model.rowCount(), 5003)


if __name__ == '__main__':
    unittest.main()
