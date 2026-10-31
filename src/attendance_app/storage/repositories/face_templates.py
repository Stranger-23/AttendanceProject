from datetime import datetime, timezone

from attendance_app.domain.errors import ValidationError, PersonNotFoundError
from attendance_app.domain.face_templates import encode_embedding, decode_embedding, DIMENSIONS, DTYPE


class FaceTemplateRepository:
    def __init__(self, database):
        self.database = database

    def list_for_person(self, person_id):
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM face_templates WHERE person_id=? ORDER BY id', (person_id,))]

    def list_active(self):
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute('''
                SELECT t.*, p.first_name, p.last_name FROM face_templates t
                JOIN people p ON p.id=t.person_id WHERE p.is_active=1
                ORDER BY t.person_id, t.id
            ''')]

    def replace(self, person_id, vectors, model_id, alignment_id, *, expected_ids, expected_registration):
        payloads = [encode_embedding(vector) for vector in vectors]
        for payload in payloads:
            decode_embedding(payload)
        with self.database.connect(write=True) as connection:
            person = connection.execute('SELECT is_active, created_at FROM people WHERE id=?', (person_id,)).fetchone()
            if person is None:
                raise PersonNotFoundError()
            if not person['is_active'] or person['created_at'] != expected_registration:
                raise ValidationError('اطلاعات فرد تغییر کرده یا فرد غیرفعال شده است. ثبت چهره را دوباره آغاز کنید.')
            actual = tuple(row[0] for row in connection.execute('SELECT id FROM face_templates WHERE person_id=? ORDER BY id', (person_id,)))
            if actual != tuple(expected_ids):
                raise ValidationError('اطلاعات چهره در این فاصله تغییر کرده است. ثبت را دوباره آغاز کنید.')
            connection.execute('DELETE FROM face_templates WHERE person_id=?', (person_id,))
            timestamp = datetime.now(timezone.utc).isoformat()
            connection.executemany('''INSERT INTO face_templates
                (person_id, embedding, dimensions, dtype, model_id, alignment_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                [(person_id, payload, DIMENSIONS, DTYPE, model_id, alignment_id, timestamp) for payload in payloads])
