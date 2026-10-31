"""Observed presence only; one row per person and Windows local calendar day."""
VERSION = 3
NAME = 'attendance'
STATEMENTS = (
    """CREATE TABLE attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        attendance_date TEXT NOT NULL CHECK(length(attendance_date)=10),
        attendance_time TEXT NOT NULL CHECK(length(attendance_time)>=14),
        observed_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'present' CHECK(status='present'),
        similarity REAL CHECK(similarity IS NULL OR similarity BETWEEN -1 AND 1),
        created_at TEXT NOT NULL,
        UNIQUE(person_id, attendance_date)
    )""",
)
