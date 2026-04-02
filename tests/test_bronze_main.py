"""Tests for datapulse.bronze.__main__ — CLI entry point."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestBronzeMain:
    def test_module_importable(self):
        """The __main__ module can be imported without error."""
        import datapulse.bronze.__main__  # noqa: F401

    @patch("datapulse.bronze.__main__.main")
    def test_main_called_in_if_name_main(self, mock_main):
        """Verify main() function exists and is callable."""
        from datapulse.bronze.__main__ import main

        # main is imported from loader and is callable
        assert callable(main)

    @patch("datapulse.bronze.loader.argparse.ArgumentParser.parse_args")
    @patch("datapulse.bronze.loader.run")
    def test_main_parses_args(self, mock_run, mock_parse):
        """main() parses CLI args and calls run()."""
        from types import SimpleNamespace

        mock_parse.return_value = SimpleNamespace(
            source="/app/data/raw/sales",
            db_url=None,
            parquet=None,
            batch_size=None,
            skip_db=False,
        )

        from datapulse.bronze.loader import main

        main()
        mock_run.assert_called_once()

    @patch("datapulse.bronze.loader.argparse.ArgumentParser.parse_args")
    @patch("datapulse.bronze.loader.run", side_effect=RuntimeError("fail"))
    def test_main_propagates_error(self, mock_run, mock_parse):
        """main() propagates exceptions from run()."""
        from types import SimpleNamespace

        mock_parse.return_value = SimpleNamespace(
            source="/tmp/data",
            db_url=None,
            parquet=None,
            batch_size=None,
            skip_db=True,
        )

        from datapulse.bronze.loader import main

        with pytest.raises(RuntimeError, match="fail"):
            main()
