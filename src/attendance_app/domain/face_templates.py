"""Portable numeric format: 128 little-endian float32 values, never pickle."""
import math
import struct

from attendance_app.domain.errors import ValidationError

DIMENSIONS = 128
DTYPE = '<f4'


def encode_embedding(values):
    try:
        values = tuple(float(value) for value in values)
        if len(values) != DIMENSIONS or not all(math.isfinite(value) for value in values):
            raise ValueError()
        length = math.sqrt(sum(value*value for value in values))
        if length <= 0:
            raise ValueError()
        return struct.pack('<128f', *(value/length for value in values))
    except (TypeError, ValueError, OverflowError, struct.error) as error:
        raise ValidationError('بردار چهره معتبر نیست.') from error


def decode_embedding(payload, dimensions=DIMENSIONS, dtype=DTYPE):
    try:
        if dimensions != DIMENSIONS or dtype != DTYPE or len(payload) != DIMENSIONS*4:
            raise ValueError()
        values = struct.unpack('<128f', payload)
        if not all(math.isfinite(value) for value in values) or not 0.99 <= sum(value*value for value in values) <= 1.01:
            raise ValueError()
        return values
    except (TypeError, ValueError, struct.error) as error:
        raise ValidationError('اطلاعات ذخیره‌شده چهره معتبر نیست.') from error
