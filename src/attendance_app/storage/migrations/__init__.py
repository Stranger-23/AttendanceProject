"""Explicit, numbered, deterministic migration registry."""
from hashlib import sha256
from attendance_app.storage.migrations import m001_people, m002_face_templates, m003_attendance, m004_settings

MIGRATIONS = (m001_people, m002_face_templates, m003_attendance, m004_settings)
TRACKING_SQL = """CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
)"""


def checksum(migration):
    return sha256("\n".join(migration.STATEMENTS).encode("utf-8")).hexdigest()


def apply_migrations(connection, migrations=MIGRATIONS):
    from datetime import datetime, timezone
    from attendance_app.domain.errors import StorageError

    ordered = sorted(migrations, key=lambda migration: migration.VERSION)
    if [m.VERSION for m in ordered] != list(range(1, len(ordered) + 1)):
        raise StorageError("ØªØ±ØªÛŒØ¨ Ù†Ø³Ø®Ù‡â€ŒÙ‡Ø§ÛŒ Ù¾Ø§ÛŒÚ¯Ø§Ù‡ Ø¯Ø§Ø¯Ù‡ Ù…Ø¹ØªØ¨Ø± Ù†ÛŒØ³Øª.")
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(TRACKING_SQL)
        applied = connection.execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version").fetchall()
        expected = [(m.VERSION, m.NAME, checksum(m)) for m in ordered]
        if [tuple(row) for row in applied] != expected[:len(applied)] or len(applied) > len(expected):
            raise StorageError("Ù†Ø³Ø®Ù‡ ÛŒØ§ Ø³Ø§Ø®ØªØ§Ø± Ù¾Ø§ÛŒÚ¯Ø§Ù‡ Ø¯Ø§Ø¯Ù‡ Ø¨Ø§ Ø§ÛŒÙ† Ø¨Ø±Ù†Ø§Ù…Ù‡ Ø³Ø§Ø²Ú¯Ø§Ø± Ù†ÛŒØ³Øª.")
        for migration in ordered[len(applied):]:
            for statement in migration.STATEMENTS:
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                               (migration.VERSION, migration.NAME, checksum(migration), datetime.now(timezone.utc).isoformat()))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
