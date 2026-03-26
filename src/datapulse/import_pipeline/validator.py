"""File validation before import."""

from pathlib import Path

from datapulse.config import settings
from datapulse.import_pipeline.models import FileFormat


ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class ValidationError(Exception):
    """Raised when file validation fails."""


def validate_file(path: Path) -> FileFormat:
    """Validate a file for import. Returns detected FileFormat.

    Raises ValidationError if the file is invalid.
    """
    if not path.exists():
        raise ValidationError(f"File not found: {path}")

    if not path.is_file():
        raise ValidationError(f"Not a file: {path}")

    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    file_size = path.stat().st_size
    if file_size == 0:
        raise ValidationError(f"File is empty: {path}")

    if file_size > settings.max_file_size_bytes:
        size_mb = file_size / (1024 * 1024)
        raise ValidationError(
            f"File too large: {size_mb:.1f}MB (max {settings.max_file_size_mb}MB)"
        )

    format_map = {".csv": FileFormat.CSV, ".xlsx": FileFormat.XLSX, ".xls": FileFormat.XLS}
    return format_map[suffix]
