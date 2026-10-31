"""Local application preferences; absence of a camera setting means index zero."""
VERSION = 4
NAME = 'settings'
STATEMENTS = (
    "CREATE TABLE settings (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)",
)
