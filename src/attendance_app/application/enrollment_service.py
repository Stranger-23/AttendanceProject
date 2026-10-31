from attendance_app.configuration.settings import EnrollmentConfig
from attendance_app.domain.errors import ValidationError
from attendance_app.recognition.engine import MODEL_ID, ALIGNMENT_ID


class EnrollmentService:
    def __init__(self, people_service, templates, config=None):
        self.people = people_service
        self.templates = templates
        self.config = config or EnrollmentConfig()

    def begin(self, person_id):
        person = self.people.get(person_id)
        if not person.is_active:
            raise ValidationError('ثبت چهره فقط برای افراد فعال ممکن است.')
        previous = self.templates.list_for_person(person_id)
        return person, tuple(row['id'] for row in previous)

    def status(self, person_id):
        rows = self.templates.list_for_person(person_id)
        return 'ثبت نشده است' if not rows else f"ثبت شده است؛ {len(rows)} نمونه"

    def save(self, person, vectors, *, expected_ids=(), replace_confirmed=False):
        if len(vectors) != self.config.samples_required:
            raise ValidationError(f'برای ثبت چهره {self.config.samples_required} نمونه لازم است.')
        if expected_ids and not replace_confirmed:
            raise ValidationError('جایگزینی اطلاعات قبلی چهره نیاز به تأیید دارد.')
        self.templates.replace(person.id, vectors, MODEL_ID, ALIGNMENT_ID,
                               expected_ids=expected_ids, expected_registration=person.created_at)
