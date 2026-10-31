"""Read-only summary of committed attendance, captured on one local calendar day."""
from dataclasses import dataclass
from attendance_app.domain.attendance import AttendanceHistoryRecord


@dataclass(frozen=True)
class DashboardSnapshot:
    captured_day: str
    registered_people: int
    active_people: int
    today_attendance: int
    total_attendance: int
    recent: tuple[AttendanceHistoryRecord, ...]
