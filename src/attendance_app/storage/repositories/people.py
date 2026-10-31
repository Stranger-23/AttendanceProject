from datetime import datetime, timezone
import sqlite3

from attendance_app.domain.errors import DuplicatePersonError, PersonNotFoundError
from attendance_app.domain.people import Person, normalize_search


class PeopleRepository:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def _person(row):
        if row is None:
            return None
        return Person(row['id'], row['person_id'], row['first_name'], row['last_name'],
                      row['optional_info'], row['created_at'], bool(row['is_active']))

    def create(self, data):
        with self.database.connect(write=True) as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO people (person_id, first_name, last_name, optional_info, created_at) VALUES (?, ?, ?, ?, ?)",
                    (data.person_id, data.first_name, data.last_name, data.optional_info, datetime.now(timezone.utc).isoformat()))
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorname == 'SQLITE_CONSTRAINT_UNIQUE':
                    raise DuplicatePersonError() from error
                raise
            row = connection.execute("SELECT * FROM people WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._person(row)

    def get(self, internal_id):
        with self.database.connect() as connection:
            return self._person(connection.execute("SELECT * FROM people WHERE id = ?", (internal_id,)).fetchone())

    def get_by_person_id(self, person_id):
        with self.database.connect() as connection:
            return self._person(connection.execute("SELECT * FROM people WHERE person_id = ?", (person_id,)).fetchone())

    def search(self, query='', *, active=True):
        term = normalize_search(query).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = '%' + term + '%'
        with self.database.connect() as connection:
            rows = connection.execute("""SELECT * FROM people WHERE is_active = ? AND (
                normalize_search(first_name || ' ' || last_name) LIKE ? ESCAPE '\\'
                OR normalize_search(person_id) LIKE ? ESCAPE '\\')
                ORDER BY last_name, first_name, id""", (int(active), pattern, pattern)).fetchall()
            return [self._person(row) for row in rows]

    def list_active(self):
        return self.search()

    def update(self, internal_id, data):
        with self.database.connect(write=True) as connection:
            try:
                cursor = connection.execute("""UPDATE people SET person_id=?, first_name=?, last_name=?, optional_info=?
                    WHERE id=?""", (data.person_id, data.first_name, data.last_name, data.optional_info, internal_id))
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorname == 'SQLITE_CONSTRAINT_UNIQUE':
                    raise DuplicatePersonError() from error
                raise
            if not cursor.rowcount:
                raise PersonNotFoundError()
            return self._person(connection.execute("SELECT * FROM people WHERE id=?", (internal_id,)).fetchone())

    def archive(self, internal_id):
        with self.database.connect(write=True) as connection:
            if not connection.execute("UPDATE people SET is_active=0 WHERE id=?", (internal_id,)).rowcount:
                raise PersonNotFoundError()
