"""CLI entry point: python -m datapulse.watcher"""

from __future__ import annotations

import argparse
import signal
import sys

from datapulse.logging import setup_logging
from datapulse.watcher.service import FileWatcherService


def main() -> None:
    parser = argparse.ArgumentParser(description="DataPulse file watcher")
    parser.add_argument(
        "--debounce",
        type=float,
        default=10.0,
        help="Seconds to wait after last file event before triggering (default: 10)",
    )
    args = parser.parse_args()

    setup_logging()
    svc = FileWatcherService()

    def _shutdown(signum, frame):
        svc.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    svc.start(debounce_seconds=args.debounce)

    # Block main thread — observer runs in background thread
    try:
        signal.pause()  # type: ignore[attr-defined]  # Not available on Windows
    except AttributeError:
        # Windows fallback
        import time

        while svc.is_running:
            time.sleep(1)


if __name__ == "__main__":
    main()
