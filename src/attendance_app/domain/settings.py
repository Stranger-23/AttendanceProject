"""Supported camera choices shared by preferences and camera dialogs."""
from attendance_app.domain.errors import ValidationError

MIN_CAMERA_INDEX = 0
MAX_CAMERA_INDEX = 16


def validate_camera_index(value):
    if type(value) is not int or not MIN_CAMERA_INDEX <= value <= MAX_CAMERA_INDEX:
        raise ValidationError('شماره دوربین باید عددی بین ۰ و ۱۶ باشد.')
    return value
