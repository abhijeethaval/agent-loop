"""Tests for AuditLogger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_loop.audit.logger import AuditEntry, AuditLogger


def _log_a_decision(logger: AuditLogger, step: int = 0) -> AuditEntry:
    return logger.log_decision(
        step=step,
        goal="g",
        history=[],
        policy_context={"org_policies": "o", "industry_rules": "i", "domain_guidelines": "d"},
        decision_type="final",
        decision_details={"final_response": "done"},
        rationale="because",
    )


class TestInMemory:
    def test_log_decision_appends(self):
        logger = AuditLogger()
        entry = _log_a_decision(logger)
        assert isinstance(entry, AuditEntry)
        assert len(logger.entries) == 1
        assert logger.entries[0].step == 0
        assert logger.entries[0].decision_output["decision_type"] == "final"

    def test_entries_returns_copy(self):
        logger = AuditLogger()
        _log_a_decision(logger)
        copy = logger.entries
        copy.clear()
        assert len(logger.entries) == 1

    def test_log_outcome_updates_matching_step(self):
        logger = AuditLogger()
        _log_a_decision(logger, step=2)
        logger.log_outcome(step=2, outcome_type="tool", status="success", result="ok")
        assert logger.entries[0].outcome == {
            "type": "tool",
            "status": "success",
            "result": "ok",
            "data": None,
        }

    def test_log_outcome_no_match_noop(self):
        logger = AuditLogger()
        _log_a_decision(logger, step=0)
        logger.log_outcome(step=99, outcome_type="tool", status="success", result="ok")
        assert logger.entries[0].outcome is None

    def test_export_session_shape(self):
        logger = AuditLogger(session_id="s1")
        _log_a_decision(logger)
        dump = logger.export_session()
        assert dump["session_id"] == "s1"
        assert len(dump["entries"]) == 1
        assert dump["entries"][0]["step"] == 0


class TestFileIO:
    def test_creates_jsonl_file(self, tmp_audit_dir: Path):
        logger = AuditLogger(log_dir=tmp_audit_dir, session_id="test")
        _log_a_decision(logger, step=0)
        _log_a_decision(logger, step=1)

        log_file = tmp_audit_dir / "session_test.jsonl"
        assert log_file.exists()

        lines = log_file.read_text().splitlines()
        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]
        assert [p["step"] for p in parsed] == [0, 1]

    def test_log_outcome_rewrites_file(self, tmp_audit_dir: Path):
        logger = AuditLogger(log_dir=tmp_audit_dir, session_id="t")
        _log_a_decision(logger, step=0)
        logger.log_outcome(step=0, outcome_type="tool", status="success", result="ok")

        log_file = tmp_audit_dir / "session_t.jsonl"
        parsed = [json.loads(line) for line in log_file.read_text().splitlines()]
        assert len(parsed) == 1
        assert parsed[0]["outcome"]["status"] == "success"

    def test_load_session_round_trip(self, tmp_audit_dir: Path):
        logger = AuditLogger(log_dir=tmp_audit_dir, session_id="rt")
        _log_a_decision(logger, step=0)
        _log_a_decision(logger, step=1)

        log_file = tmp_audit_dir / "session_rt.jsonl"
        loaded = AuditLogger.load_session(log_file)
        assert len(loaded.entries) == 2
        assert [e.step for e in loaded.entries] == [0, 1]


def test_session_id_defaulted_to_timestamp():
    logger = AuditLogger()
    assert logger.session_id  # non-empty timestamp string


def test_no_log_dir_does_not_create_files(tmp_path: Path):
    logger = AuditLogger()
    _log_a_decision(logger)
    # No file should be created anywhere tied to tmp_path; just assert no crash.
    assert logger.entries[0].step == 0
    with pytest.raises(FileNotFoundError):
        # Sanity: load_session requires a real file.
        AuditLogger.load_session(tmp_path / "nope.jsonl")
