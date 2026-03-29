"""Shared types and validators used across DataPulse modules.

Centralizes common type aliases and security validators to avoid duplication.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import PlainSerializer

# Decimal that serializes as a JSON number (float) instead of a string.
# Used for financial values in API responses where JSON parsers expect numbers.
JsonDecimal = Annotated[Decimal, PlainSerializer(float, return_type=float)]


def validate_source_dir(v: str, allowed_root: str = "/app/data") -> str:
    """Validate that a source directory path is inside the allowed root.

    Prevents path traversal attacks by:
    1. Rejecting '..' path components
    2. Using PurePosixPath.is_relative_to() instead of str.startswith()
       (startswith is vulnerable: '/app/data_evil' starts with '/app/data')

    Args:
        v: The path to validate.
        allowed_root: The root directory paths must be inside.

    Returns:
        The normalized path string.

    Raises:
        ValueError: If the path contains '..' or is outside the allowed root.
    """
    normalized = PurePosixPath(v)
    if ".." in normalized.parts:
        raise ValueError("source_dir must not contain '..'")
    root = PurePosixPath(allowed_root)
    if not normalized.is_relative_to(root):
        raise ValueError(f"source_dir must be inside {root}")
    return str(normalized)
