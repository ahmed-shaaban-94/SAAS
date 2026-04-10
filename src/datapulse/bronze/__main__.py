"""Allow running: python -m datapulse.bronze.loader --source <dir>"""

from datapulse.bronze.loader import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, ValueError) as e:
        import sys

        print(f"Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)
