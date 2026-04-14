"""Registry of available bronze data loaders.

Concrete loader classes register themselves here on import so that the
pipeline executor can discover and invoke them by name.

Usage::

    from datapulse.bronze.registry import LOADER_REGISTRY

    loader_class = LOADER_REGISTRY["stock_receipts"]
    result = loader_class(data_dir).run(engine, tenant_id=tenant_id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datapulse.bronze.base_loader import BronzeLoader

# Maps a logical source name to the concrete BronzeLoader subclass.
# Populated by each loader module on import, e.g.:
#   from datapulse.bronze.registry import LOADER_REGISTRY
#   LOADER_REGISTRY["stock_receipts"] = ExcelReceiptsLoader
LOADER_REGISTRY: dict[str, type[BronzeLoader]] = {}
