"""Export a captured report using same-directory staging and atomic publication."""
from pathlib import Path
import os
import tempfile

from attendance_app.domain.errors import ExportError
from attendance_app.reporting.excel import ExcelWriter


class ExportService:
    def __init__(self, date_formatter, writer=None):
        self.date_formatter = date_formatter
        self.writer = writer or ExcelWriter()

    def export(self, snapshot, path, *, overwrite=False):
        if not snapshot.records:
            raise ExportError('گزارش خالی قابل خروجی گرفتن نیست.')
        destination = Path(path)
        if destination.suffix.lower() != '.xlsx':
            raise ExportError('پسوند فایل باید xlsx باشد.')
        temporary = None
        try:
            if destination.exists() and not overwrite:
                raise ExportError('فایل وجود دارد؛ جایگزینی آن نیاز به تأیید دارد.')
            filters = snapshot.filters
            rows = tuple((r.full_name, r.public_person_id, self.date_formatter(r.attendance_date),
                          r.attendance_time[:8], 'حاضر') for r in snapshot.records)
            metadata = (
                ('جست‌وجو', filters.query or 'بدون جست‌وجو'), ('فرد', snapshot.person_label),
                ('از تاریخ', self.date_formatter(filters.start_date) if filters.start_date else 'همه تاریخها'),
                ('تا تاریخ', self.date_formatter(filters.end_date) if filters.end_date else 'همه تاریخها'),
                ('وضعیت', 'حاضر' if filters.status else 'همه وضعیتها'),
                ('زمان تهیه گزارش', self.date_formatter(snapshot.captured_at.date().isoformat())
                 + ' ' + snapshot.captured_at.strftime('%H:%M:%S %z')),
                ('تعداد حضورهای ثبت‌شده (نفر-روز)', snapshot.record_count),
                ('تعداد افراد دارای حضور', snapshot.people_count),
                ('مبنای خروجی', 'همان پیش‌نمایش و ترتیب نمایش داده‌شده'),
            )
            descriptor, temporary = tempfile.mkstemp(prefix='.attendance-', suffix='.xlsx', dir=destination.parent)
            os.close(descriptor)
            self.writer.write(Path(temporary), rows, metadata)
            if overwrite:
                os.replace(temporary, destination)
            else:
                # Atomic no-clobber publication, including a file created after Save.
                if os.name == 'nt':
                    os.rename(temporary, destination)
                else:
                    os.link(temporary, destination)
                    os.unlink(temporary)
            temporary = None
            return destination
        except ExportError:
            raise
        except Exception as error:
            raise ExportError('ذخیره اکسل ممکن نشد؛ فضای دیسک، دسترسی مسیر و باز بودن فایل را بررسی کنید.') from error
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
