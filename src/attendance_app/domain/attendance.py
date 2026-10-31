"""Committed attendance receipt, independent of camera and UI."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AttendanceReceipt:
    id: int
    person_id: int
    attendance_date: str
    attendance_time: str
    observed_at: str
    status: str
    similarity: float | None
    created_at: str
    created: bool


@dataclass(frozen=True)
class AttendanceHistoryRecord:
    id: int
    person_id: int
    public_person_id: str
    full_name: str
    is_active: bool
    attendance_date: str
    attendance_time: str
    status: str


@dataclass(frozen=True)
class HistoryPerson:
    id: int
    public_person_id: str
    full_name: str
    is_active: bool
