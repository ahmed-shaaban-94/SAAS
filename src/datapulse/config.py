"""Backwards-compatibility shim — the canonical location is datapulse.core.config.

All public symbols (Settings, get_settings) are re-exported here so that
existing ``from datapulse.config import ...`` statements continue to work.
"""

from datapulse.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
