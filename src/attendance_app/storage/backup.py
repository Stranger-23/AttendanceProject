"""Validated SQLite snapshots and transactional restore without replacing open files."""
from contextlib import closing
from datetime import datetime, timezone, date, time
from pathlib import Path
import os
import sqlite3
import tempfile
from uuid import uuid4

from attendance_app.domain.errors import StorageError
from attendance_app.storage.migrations import apply_migrations, MIGRATIONS
from attendance_app.domain.face_templates import decode_embedding
from attendance_app.domain.errors import ValidationError


def schema(connection):
    return connection.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name").fetchall()


class BackupManager:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def validate(connection):
        connection.execute("PRAGMA trusted_schema=OFF")
        # Compare against the exact supported version before upgrading a private snapshot.
        count = connection.execute('SELECT count(*) FROM schema_migrations').fetchone()[0]
        if not 1 <= count <= len(MIGRATIONS):
            raise StorageError('نسخه فایل پشتیبان پشتیبانی نمی‌شود.')
        with closing(sqlite3.connect(':memory:', isolation_level=None)) as expected:
            apply_migrations(expected, MIGRATIONS[:count])
            if [tuple(row) for row in schema(connection)] != schema(expected):
                raise StorageError("فایل انتخاب‌شده پشتیبان سازگار این نسخه از برنامه نیست.")
            actual_versions = [tuple(row) for row in connection.execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version")]
            expected_versions = expected.execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version").fetchall()
            if actual_versions != expected_versions:
                raise StorageError("نسخه پشتیبان با این برنامه سازگار نیست.")
        if connection.execute("PRAGMA integrity_check").fetchall() != [('ok',)] or connection.execute("PRAGMA foreign_key_check").fetchall():
            raise StorageError("فایل پشتیبان آسیب‌دیده است.")
        for row in connection.execute("SELECT person_id, first_name, last_name, optional_info, created_at FROM people"):
            if not all(isinstance(value, str) for value in row):
                raise StorageError("اطلاعات فایل پشتیبان معتبر نیست.")
            try:
                datetime.fromisoformat(row[4])
            except ValueError as error:
                raise StorageError("تاریخ‌های فایل پشتیبان معتبر نیست.") from error
        if count >= 2:
            for row in connection.execute('SELECT embedding, dimensions, dtype, created_at FROM face_templates'):
                try:
                    decode_embedding(row[0], row[1], row[2])
                    datetime.fromisoformat(row[3])
                except (ValidationError, ValueError, TypeError) as error:
                    raise StorageError('اطلاعات چهره در فایل پشتیبان معتبر نیست.') from error
        if count >= 3:
            for row in connection.execute('SELECT attendance_date, attendance_time, observed_at, created_at FROM attendance'):
                try:
                    local = datetime.combine(date.fromisoformat(row[0]), time.fromisoformat(row[1]))
                    observed, created = datetime.fromisoformat(row[2]), datetime.fromisoformat(row[3])
                    if local.utcoffset() is None or observed.utcoffset() is None or created.utcoffset() is None:
                        raise ValueError()
                    if local != observed.replace(microsecond=0):
                        raise ValueError()
                except (ValueError, TypeError) as error:
                    raise StorageError('زمان ثبت حضور در فایل پشتیبان معتبر نیست.') from error

    def backup(self, destination, *, overwrite=False):
        destination = Path(destination).resolve()
        if destination == self.database.path.resolve():
            raise StorageError("مسیر پشتیبان باید با فایل اصلی متفاوت باشد.")
        if destination.suffix.lower() != '.db':
            raise StorageError("پسوند فایل پشتیبان باید .db باشد.")
        if destination.exists() and not overwrite:
            raise StorageError("جایگزینی فایل پشتیبان نیاز به تأیید دارد.")
        stage = None
        try:
            with self.database.lock:
                descriptor, stage = tempfile.mkstemp(suffix='.db', dir=destination.parent)
                os.close(descriptor)
                with self.database.connect() as source, closing(sqlite3.connect(stage)) as target:
                    source.backup(target)
                    self.validate(target)
                if not overwrite:
                    # Exclusive reservation prevents silently replacing a concurrently created file.
                    with destination.open('xb'):
                        pass
                os.replace(stage, destination)
        except (sqlite3.Error, OSError) as error:
            raise StorageError("تهیه نسخه پشتیبان انجام نشد. مسیر و دسترسی فایل را بررسی کنید.") from error
        finally:
            if stage is not None:
                Path(stage).unlink(missing_ok=True)

    def restore(self, source, *, confirmed=False):
        if not confirmed:
            raise StorageError("بازیابی و جایگزینی اطلاعات نیاز به تأیید دارد.")
        source = Path(source).resolve()
        if source == self.database.path.resolve():
            raise StorageError("فایل اصلی را نمی‌توان به عنوان پشتیبان بازیابی کرد.")
        stage = None
        try:
            with self.database.lock:
                descriptor, stage = tempfile.mkstemp(suffix='.db', dir=self.database.path.parent)
                os.close(descriptor)
                # Read-only source, then validate a stable private snapshot before any live writes.
                with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as backup, closing(sqlite3.connect(stage)) as snapshot:
                    backup.backup(snapshot)
                    self.validate(snapshot)
                    apply_migrations(snapshot)
                    self.validate(snapshot)
                    recovery_dir = self.database.path.parent / 'backups'
                    recovery_dir.mkdir(exist_ok=True)
                    recovery = recovery_dir / ('before-restore-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex + '.db')
                    self.backup(recovery)
                    with self.database.connect() as live:
                        # SQLite backup holds the destination write transaction atomically.
                        snapshot.backup(live)
                return recovery
        except (sqlite3.Error, OSError) as error:
            raise StorageError("بازیابی انجام نشد. سالم بودن فایل پشتیبان و دسترسی به آن را بررسی کنید.") from error
        finally:
            if stage is not None:
                Path(stage).unlink(missing_ok=True)
