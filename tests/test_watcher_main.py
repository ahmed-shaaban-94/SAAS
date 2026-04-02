"""Tests for datapulse.watcher.__main__ — basic import and structure."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_module_importable():
    """The watcher __main__ module is importable."""
    import datapulse.watcher.__main__ as mod

    assert hasattr(mod, "main")
    assert callable(mod.main)


@patch("datapulse.watcher.__main__.FileWatcherService")
@patch("datapulse.watcher.__main__.setup_logging")
@patch("datapulse.watcher.__main__.signal")
@patch("datapulse.watcher.__main__.argparse.ArgumentParser")
def test_main_wires_up_service(mock_argparse, mock_signal, mock_logging, mock_svc_cls):
    """main() creates a FileWatcherService and calls start()."""
    from datapulse.watcher.__main__ import main

    # Mock argparse
    mock_parser = MagicMock()
    mock_argparse.return_value = mock_parser
    mock_args = MagicMock()
    mock_args.debounce = 10.0
    mock_parser.parse_args.return_value = mock_args

    # Mock signal.pause to raise AttributeError (Windows path)
    mock_signal.pause = None  # simulates missing attribute
    del mock_signal.pause  # forces AttributeError in hasattr

    # Mock service to not actually run
    mock_svc = MagicMock()
    mock_svc.is_running = False  # exit the Windows while loop immediately
    mock_svc_cls.return_value = mock_svc

    main()

    mock_logging.assert_called_once()
    mock_svc_cls.assert_called_once()
    mock_svc.start.assert_called_once_with(debounce_seconds=10.0)
