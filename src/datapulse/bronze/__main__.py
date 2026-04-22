"""Allow running: python -m datapulse.bronze.loader --source <dir>"""

from __future__ import annotations

import sys

import structlog

from datapulse.bronze.loader import main

log = structlog.get_logger(__name__)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        # Container log collectors expect JSON — structlog emits structured
        # output matching the rest of the pipeline. A plain print() here
        # would corrupt downstream log parsing (#548-6).
        log.exception("bronze_pipeline_failed")
        sys.exit(1)
