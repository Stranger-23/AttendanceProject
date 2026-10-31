from datetime import datetime
from PySide6.QtCore import QCalendar, QDate


PERSIAN_CALENDAR = QCalendar(QCalendar.System.Jalali)


def attendance_date(iso_date):
    """Format the saved local day without converting timestamps or timezones."""
    day = QDate.fromString(iso_date, 'yyyy-MM-dd')
    if not day.isValid():
        raise ValueError('Invalid attendance date')
    return day.toString('yyyy/MM/dd', PERSIAN_CALENDAR)


def canonical_date(day):
    """QDate represents an absolute day even when edited with a Jalali calendar."""
    if not day.isValid():
        raise ValueError('Invalid selected date')
    return day.toString('yyyy-MM-dd')


def registration_date(timestamp):
    return datetime.fromisoformat(timestamp).astimezone().strftime('%Y/%m/%d %H:%M')
