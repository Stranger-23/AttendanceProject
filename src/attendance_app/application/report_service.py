"""Read-only reports reuse the accepted History validation and query path."""
from datetime import datetime

from attendance_app.domain.errors import ValidationError
from attendance_app.domain.reports import ReportFilters, ReportSnapshot


class ReportService:
    def __init__(self, attendance_service):
        self.attendance = attendance_service

    def read(self, filters):
        if not isinstance(filters, ReportFilters) or filters.status not in (None, 'present'):
            raise ValidationError('وضعیت گزارش معتبر نیست.')
        records = tuple(self.attendance.search_history(
            filters.query, person_id=filters.person_id,
            start_date=filters.start_date, end_date=filters.end_date))
        people = tuple(self.attendance.list_history_people())
        label = next((f'{p.full_name} · {p.public_person_id}' for p in people
                      if p.id == filters.person_id), 'همه افراد')
        return ReportSnapshot(filters, records, datetime.now().astimezone(), label), people
