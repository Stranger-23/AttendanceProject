"""Validated camera preference, read afresh so restore needs no cache invalidation."""
from attendance_app.domain.errors import StorageError, ValidationError
from attendance_app.domain.settings import validate_camera_index


class SettingsService:
    def __init__(self, repository):
        self.repository = repository

    def camera_index(self):
        value = self.repository.get('camera_index')
        if value is None:
            return 0
        try:
            return validate_camera_index(int(value))
        except (ValueError, TypeError, ValidationError) as error:
            raise StorageError('تنظیم ذخیره‌شده دوربین معتبر نیست؛ آن را در تنظیمات دوباره ذخیره کنید.') from error

    def save_camera_index(self, value):
        self.repository.set('camera_index', str(validate_camera_index(value)))
