"""Workbook generation only: receives prepared text, never queries SQLite or Qt."""
from itertools import chain
from attendance_app.domain.errors import ExportError


HEADERS = ('نام و نام خانوادگی', 'شناسه فرد', 'تاریخ حضور', 'ساعت حضور', 'وضعیت حضور')
MAX_RECORDS = 1_048_575
MAX_TEXT = 32767


class ExcelWriter:
    def write(self, path, rows, metadata):
        import xlsxwriter

        if len(rows) > MAX_RECORDS:
            raise ExportError('تعداد رکوردها از ظرفیت اکسل بیشتر است؛ محدوده گزارش را کوچک‌تر کنید.')
        if any(isinstance(value, str) and len(value) > MAX_TEXT
               for row in chain(metadata, rows) for value in row):
            raise ExportError('متن گزارش از ظرفیت یک سلول اکسل بیشتر است.')
        with xlsxwriter.Workbook(str(path), {
            'constant_memory': True, 'strings_to_formulas': False,
            'strings_to_urls': False, 'strings_to_numbers': False,
        }) as book:
            normal = book.add_format({'font_name': 'IRANSans', 'font_size': 11,
                                      'align': 'right', 'reading_order': 2, 'num_format': '@'})
            count = book.add_format({'font_name': 'IRANSans', 'font_size': 11,
                                     'align': 'right', 'num_format': '#,##0'})
            heading = book.add_format({'font_name': 'IRANSans', 'font_size': 11,
                                       'bold': True, 'bg_color': '#7257FF', 'font_color': '#FFFFFF',
                                       'align': 'right', 'reading_order': 2, 'text_wrap': True})
            info = book.add_worksheet('اطلاعات گزارش')
            info.right_to_left()
            info.hide_gridlines(2)
            info.set_column(0, 0, 30)
            info.set_column(1, 1, 65)
            info.write_string(0, 0, 'گزارش حضور ثبت‌شده', heading)
            info.set_row(0, 30)
            for index, pair in enumerate(metadata, 2):
                for column, value in enumerate(pair):
                    if isinstance(value, int):
                        info.write_number(index, column, value, count)
                    else:
                        info.write_string(index, column, value, normal)
            sheet = book.add_worksheet('حضورهای ثبت‌شده')
            sheet.right_to_left()
            sheet.hide_gridlines(2)
            for column, width in enumerate((34, 25, 19, 17, 18)):
                sheet.set_column(column, column, width)
                sheet.write_string(0, column, HEADERS[column], heading)
            sheet.set_row(0, 32)
            for index, row in enumerate(rows, 1):
                sheet.set_row(index, 24)
                for column, value in enumerate(row):
                    if sheet.write_string(index, column, value, normal) != 0:
                        raise ExportError('نوشتن کامل گزارش در اکسل ممکن نشد.')
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, len(rows), 4)
