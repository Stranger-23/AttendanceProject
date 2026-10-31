"""Safe, user-facing failures shared across application boundaries."""
class AppError(Exception):
    pass


class ExportError(AppError):
    pass


class ValidationError(AppError):
    pass


class DuplicatePersonError(AppError):
    def __init__(self):
        super().__init__("این شناسه قبلاً ثبت شده است؛ افراد بایگانی‌شده را نیز بررسی کنید.")


class PersonNotFoundError(AppError):
    def __init__(self):
        super().__init__("فرد مورد نظر پیدا نشد. فهرست را تازه‌سازی کنید.")


class StorageError(AppError):
    def __init__(self, message="دسترسی به اطلاعات ممکن نشد. مسیر و دسترسی فایل یا باز بودن آن در برنامه‌ای دیگر را بررسی کنید."):
        super().__init__(message)
