from __future__ import annotations

import importlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from spectralbridge import qa_dashboard, qa_plots
from spectralbridge.cli import recover_cli
from spectralbridge.corrections import log_stats
from spectralbridge.logging_utils import configure_cli_logging


def test_configure_cli_logging_only_initializes_unconfigured_root(monkeypatch) -> None:
    calls: list[int] = []
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: calls.append(kwargs["level"]))
    root_logger.handlers = []
    try:
        configure_cli_logging()
        assert calls == [logging.INFO]

        calls.clear()
        root_logger.handlers = [logging.NullHandler()]
        configure_cli_logging()
        assert calls == []
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def test_qa_plots_import_does_not_force_info_level() -> None:
    qa_logger = logging.getLogger("spectralbridge.qa_plots")
    previous_level = qa_logger.level
    try:
        qa_logger.setLevel(logging.NOTSET)
        importlib.reload(qa_plots)
        assert logging.getLogger("spectralbridge.qa_plots").level == logging.NOTSET
    finally:
        qa_logger.setLevel(previous_level)


def test_log_stats_uses_module_logger(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="spectralbridge.corrections")
    log_stats("demo", np.array([1.0, 2.0], dtype=np.float32))
    assert "demo: min=1.000000 max=2.000000" in caplog.text


def test_qa_dashboard_main_uses_shared_cli_logging(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    monkeypatch.setattr(qa_dashboard, "configure_cli_logging", lambda: calls.append("configured"))
    monkeypatch.setattr(qa_dashboard, "collect_qa_metrics", lambda base_folder: pd.DataFrame())

    qa_dashboard.main(["--base-folder", str(tmp_path)])

    assert calls == ["configured"]


def test_recover_cli_main_uses_shared_cli_logging(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    monkeypatch.setattr(recover_cli, "configure_cli_logging", lambda: calls.append("configured"))

    recover_cli.main(["--base-folder", str(tmp_path)])

    assert calls == ["configured"]
