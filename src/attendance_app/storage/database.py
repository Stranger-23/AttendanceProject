"""Short-lived, thread-owned SQLite connections; no UI dependencies."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from threading import RLock

from attendance_app.domain.errors import StorageError
from attendance_app.domain.people import normalize_search
from attendance_app.storage.migrations import apply_migrations


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock = RLock()

    @contextmanager
    def connect(self, *, write=False):
        connection = None
        with self.lock:
            try:
                connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("PRAGMA trusted_schema = OFF")
                connection.create_function("normalize_search", 1, normalize_search, deterministic=True)
                if write:
                    connection.execute("BEGIN IMMEDIATE")
                yield connection
                if write:
                    connection.commit()
            except (sqlite3.Error, OSError) as error:
                if connection is not None:
                    connection.rollback()
                raise StorageError() from error
            except Exception:
                if connection is not None:
                    connection.rollback()
                raise
            finally:
                if connection is not None:
                    connection.close()

    def initialize(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connect() as connection:
                apply_migrations(connection)
        except OSError as error:
            raise StorageError() from error
