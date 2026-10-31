"""Immutable report inputs and the exact attendance snapshot shown to an operator."""
from dataclasses import dataclass
from datetime import datetime

from attendance_app.domain.attendance import AttendanceHistoryRecord


@dataclass(frozen=True)
class ReportFilters:
    query: str = ''
    person_id: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class ReportSnapshot:
    filters: ReportFilters
    records: tuple[AttendanceHistoryRecord, ...]
    captured_at: datetime
    person_label: str

    @property
    def record_count(self):
        return len(self.records)

    @property
    def people_count(self):
        return len({record.person_id for record in self.records})
