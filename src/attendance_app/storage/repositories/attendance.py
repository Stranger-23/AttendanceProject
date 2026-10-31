from datetime import datetime, timezone
import math

from attendance_app.domain.attendance import AttendanceReceipt, AttendanceHistoryRecord, HistoryPerson
from attendance_app.domain.errors import ValidationError
from attendance_app.domain.people import normalize_search
from attendance_app.domain.dashboard import DashboardSnapshot


class AttendanceRepository:
    def __init__(self, database):
        self.database = database

    def dashboard_snapshot(self, captured_day):
        with self.database.connect() as connection:
            # Autocommit connections otherwise give each SELECT a different snapshot.
            # Deferred BEGIN acquires only a read snapshot, never a write reservation.
            connection.execute('BEGIN')
            counts = dict(connection.execute('''SELECT
                (SELECT COUNT(*) FROM people) AS registered_people,
                (SELECT COUNT(*) FROM people WHERE is_active = 1) AS active_people,
                (SELECT COUNT(*) FROM attendance WHERE attendance_date = ?) AS today_attendance,
                (SELECT COUNT(*) FROM attendance) AS total_attendance''', (captured_day,)).fetchone())
            rows = connection.execute('''SELECT a.id, a.person_id, p.person_id AS public_person_id,
                p.first_name || ' ' || p.last_name AS full_name, p.is_active,
                a.attendance_date, a.attendance_time, a.status
                FROM attendance a JOIN people p ON p.id=a.person_id
                ORDER BY a.attendance_date DESC, substr(a.attendance_time,1,8) DESC, a.id DESC
                LIMIT ?''', (10,)).fetchall()
            recent = tuple(AttendanceHistoryRecord(**{**dict(row), 'is_active': bool(row['is_active'])})
                           for row in rows)
            connection.commit()
        return DashboardSnapshot(captured_day=captured_day, recent=recent, **counts)

    def search(self, query='', *, person_id=None, start_date=None, end_date=None):
        conditions, parameters = [], []
        term = normalize_search(query)
        if term:
            term = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            conditions.append("""(normalize_search(p.first_name || ' ' || p.last_name) LIKE ? ESCAPE '\\'
                OR normalize_search(p.person_id) LIKE ? ESCAPE '\\')""")
            parameters.extend(('%' + term + '%', '%' + term + '%'))
        for value, clause in ((person_id, 'a.person_id = ?'),
                              (start_date, 'a.attendance_date >= ?'), (end_date, 'a.attendance_date <= ?')):
            if value is not None:
                conditions.append(clause)
                parameters.append(value)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        with self.database.connect() as connection:
            rows = connection.execute('''SELECT a.id, a.person_id, p.person_id AS public_person_id,
                p.first_name || ' ' || p.last_name AS full_name, p.is_active,
                a.attendance_date, a.attendance_time, a.status
                FROM attendance a JOIN people p ON p.id=a.person_id''' + where + '''
                ORDER BY a.attendance_date DESC, substr(a.attendance_time,1,8) DESC, a.id DESC''', parameters).fetchall()
            return [AttendanceHistoryRecord(**{**dict(row), 'is_active': bool(row['is_active'])}) for row in rows]

    def list_history_people(self):
        with self.database.connect() as connection:
            rows = connection.execute('''SELECT p.id, p.person_id AS public_person_id,
                p.first_name || ' ' || p.last_name AS full_name, p.is_active
                FROM people p WHERE EXISTS (SELECT 1 FROM attendance a WHERE a.person_id=p.id)
                ORDER BY p.last_name, p.first_name, p.id''').fetchall()
            return [HistoryPerson(**{**dict(row), 'is_active': bool(row['is_active'])}) for row in rows]

    def record(self, person_id, observed_at, similarity=None):
        if (type(person_id) is not int or person_id <= 0
                or not isinstance(observed_at, datetime) or observed_at.utcoffset() is None):
            raise ValidationError('شناسه فرد یا زمان مشاهده معتبر نیست.')
        if similarity is not None and (not isinstance(similarity, (int, float))
                                       or not math.isfinite(similarity) or not -1 <= similarity <= 1):
            raise ValidationError('امتیاز شناسایی معتبر نیست.')
        day = observed_at.date().isoformat()
        local_time = observed_at.timetz().isoformat(timespec='seconds')
        with self.database.connect(write=True) as connection:
            # Recheck the live roster under the same write transaction as the insert.
            eligible = connection.execute('''SELECT 1 FROM people p WHERE p.id=? AND p.is_active=1
                AND EXISTS (SELECT 1 FROM face_templates t WHERE t.person_id=p.id)''', (person_id,)).fetchone()
            if not eligible:
                raise ValidationError('ثبت حضور فقط برای فرد فعال دارای چهره ثبت‌شده ممکن است.')
            cursor = connection.execute('''INSERT INTO attendance
                (person_id, attendance_date, attendance_time, observed_at, status, similarity, created_at)
                VALUES (?, ?, ?, ?, 'present', ?, ?)
                ON CONFLICT(person_id, attendance_date) DO NOTHING''',
                (person_id, day, local_time, observed_at.astimezone(timezone.utc).isoformat(),
                 similarity, datetime.now(timezone.utc).isoformat()))
            created = cursor.rowcount == 1
            row = dict(connection.execute('SELECT * FROM attendance WHERE person_id=? AND attendance_date=?',
                                          (person_id, day)).fetchone())
        # The context manager has committed before a success receipt can escape.
        return AttendanceReceipt(**row, created=created)
