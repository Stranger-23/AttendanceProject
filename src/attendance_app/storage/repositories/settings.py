"""Local key/value persistence using thread-owned database connections."""
class SettingsRepository:
    def __init__(self, database):
        self.database = database

    def get(self, key):
        with self.database.connect() as connection:
            row = connection.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row[0] if row else None

    def set(self, key, value):
        with self.database.connect(write=True) as connection:
            connection.execute('INSERT INTO settings(key, value) VALUES (?, ?) '
                               'ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
