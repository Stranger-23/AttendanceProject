"""Confirmed presence recording and validated read-only history use cases."""
from datetime import date

from attendance_app.domain.errors import ValidationError


class AttendanceService:
    def __init__(self, repository):
        self.repository = repository

    def record(self, result, observed_at):
        # RecognitionEngine.recognize masks unconfirmed identities as unknown.
        if result.state != 'known' or result.person_id is None:
            return None
        return self.repository.record(result.person_id, observed_at, result.similarity)

    def search_history(self, query='', *, person_id=None, start_date=None, end_date=None):
        if not isinstance(query, str) or (person_id is not None and (type(person_id) is not int or person_id <= 0)):
            raise ValidationError('فیلتر جست‌وجو یا فرد معتبر نیست.')
        for value in (start_date, end_date):
            if value is not None:
                try:
                    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                        raise ValueError()
                except (ValueError, TypeError):
                    raise ValidationError('تاریخ انتخاب‌شده معتبر نیست.') from None
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValidationError('تاریخ آغاز باید پیش از تاریخ پایان یا برابر با آن باشد.')
        return self.repository.search(query, person_id=person_id, start_date=start_date, end_date=end_date)

    def list_history_people(self):
        return self.repository.list_history_people()

    def get_dashboard_snapshot(self, captured_day):
        try:
            if not isinstance(captured_day, str) or date.fromisoformat(captured_day).isoformat() != captured_day:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValidationError('تاریخ داشبورد معتبر نیست.') from None
        return self.repository.dashboard_snapshot(captured_day)
