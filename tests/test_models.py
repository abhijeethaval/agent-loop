"""Tests for Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_loop.models.policy_context import PolicyContext
from agent_loop.models.state import AgentState, HistoryEntry
from agent_loop.models.tool_result import ToolResult


class TestToolResult:
    def test_success_factory(self):
        r = ToolResult.success("ok", data={"k": 1})
        assert r.status == "success"
        assert r.message == "ok"
        assert r.data == {"k": 1}

    def test_error_factory(self):
        r = ToolResult.error("bad")
        assert r.status == "error"
        assert r.message == "bad"
        assert r.data is None

    def test_status_literal_enforced(self):
        with pytest.raises(ValidationError):
            ToolResult(status="weird", message="x")

    def test_message_required(self):
        with pytest.raises(ValidationError):
            ToolResult(status="success")


class TestHistoryEntry:
    def test_minimal_entry(self):
        e = HistoryEntry(step=0, actor="agent", action="think", outcome="success", result="done")
        assert e.arguments is None

    def test_actor_literal_enforced(self):
        with pytest.raises(ValidationError):
            HistoryEntry(step=0, actor="robot", action="x", outcome="success", result="y")

    def test_outcome_literal_enforced(self):
        with pytest.raises(ValidationError):
            HistoryEntry(step=0, actor="agent", action="x", outcome="meh", result="y")


class TestAgentState:
    def test_defaults(self):
        s = AgentState(goal="do the thing")
        assert s.user_messages == []
        assert s.history == []
        assert s.final_response is None

    def test_add_history_entry_appends(self):
        s = AgentState(goal="g")
        s.add_history_entry(
            step=1,
            actor="tool",
            action="echo",
            outcome="success",
            result="hi",
            arguments={"text": "hi"},
        )
        assert len(s.history) == 1
        entry = s.history[0]
        assert entry.step == 1
        assert entry.actor == "tool"
        assert entry.arguments == {"text": "hi"}

    def test_get_history_dicts_serializes(self):
        s = AgentState(goal="g")
        s.add_history_entry(step=1, actor="agent", action="a", outcome="success", result="r")
        dicts = s.get_history_dicts()
        assert len(dicts) == 1
        assert dicts[0]["actor"] == "agent"
        assert dicts[0]["action"] == "a"
        assert dicts[0]["step"] == 1


class TestPolicyContext:
    def test_defaults_empty_strings(self):
        ctx = PolicyContext()
        assert ctx.org_policies == ""
        assert ctx.industry_rules == ""
        assert ctx.domain_guidelines == ""

    def test_custom_values(self):
        ctx = PolicyContext(
            org_policies="org",
            industry_rules="ind",
            domain_guidelines="dom",
        )
        assert ctx.org_policies == "org"
        assert ctx.industry_rules == "ind"
        assert ctx.domain_guidelines == "dom"
