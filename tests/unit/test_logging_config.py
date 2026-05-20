from __future__ import annotations

import json
import logging
from io import StringIO

import pytest
import structlog

from app import logging_config


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    monkeypatch.setattr(logging_config, "_configured", False)
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


class TestConfigureLogging:
    def test_idempotent_without_force(self, monkeypatch):
        logging_config.configure_logging()
        first_processors = structlog.get_config()["processors"]
        logging_config.configure_logging()
        assert structlog.get_config()["processors"] is first_processors

    def test_force_reinitializes(self):
        logging_config.configure_logging()
        first_processors = structlog.get_config()["processors"]
        logging_config.configure_logging(force=True)
        assert structlog.get_config()["processors"] is not first_processors

    def test_invalid_log_level_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "NOT_A_LEVEL")
        logging_config.configure_logging(force=True)
        assert logging.getLogger().level == logging.INFO

    def test_log_level_respected(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        logging_config.configure_logging(force=True)
        assert logging.getLogger().level == logging.DEBUG

    def test_emits_json(self, capsys):
        logging_config.configure_logging(force=True)
        logger = structlog.get_logger("app.test")
        logger.info("event.fired", key="value", number=42)
        captured = capsys.readouterr()
        line = captured.err.strip().splitlines()[-1]
        payload = json.loads(line)
        assert payload["event"] == "event.fired"
        assert payload["key"] == "value"
        assert payload["number"] == 42
        assert payload["level"] == "info"
        assert "timestamp" in payload

    def test_stdlib_logging_bridged(self):
        logging_config.configure_logging(force=True)
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_get_logger_returns_bound_logger(self):
        logging_config.configure_logging(force=True)
        logger = logging_config.get_logger("custom")
        assert hasattr(logger, "info")
        assert hasattr(logger, "bind")
