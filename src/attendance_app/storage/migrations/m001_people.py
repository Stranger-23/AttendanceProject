"""First schema: people only. No attendance or facial data."""
VERSION = 1
NAME = "people"
STATEMENTS = (
    """CREATE TABLE people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id TEXT NOT NULL UNIQUE CHECK(length(trim(person_id)) > 0),
        first_name TEXT NOT NULL CHECK(length(trim(first_name)) > 0),
        last_name TEXT NOT NULL CHECK(length(trim(last_name)) > 0),
        optional_info TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
    )""",
    "CREATE INDEX idx_people_active_name ON people(is_active, last_name, first_name, id)",
)
