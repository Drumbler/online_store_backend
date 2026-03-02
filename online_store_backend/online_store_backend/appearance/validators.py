"""Валидаторы файлов логотипа магазина."""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from PIL import Image

ALLOWED_LOGO_EXTENSIONS = ("png", "jpg", "jpeg", "webp")
MAX_LOGO_FILE_SIZE_BYTES = 512 * 1024


def validate_logo_extension(value):
    """Проверяет допустимое расширение файла логотипа."""
    validator = FileExtensionValidator(allowed_extensions=list(ALLOWED_LOGO_EXTENSIONS))
    validator(value)


def validate_logo_file(value):
    """Проверяет размер и квадратные пропорции изображения логотипа."""
    validate_logo_extension(value)
    if value.size > MAX_LOGO_FILE_SIZE_BYTES:
        raise ValidationError("Logo file size must be 512KB or less.")

    value.seek(0)
    with Image.open(value) as image:
        width, height = image.size
    value.seek(0)

    if width != height:
        raise ValidationError("Logo image must be square.")
