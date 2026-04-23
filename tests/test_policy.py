"""Tests for policy normalization and DecisionOutput."""

from __future__ import annotations

from agent_loop.policy.policy import AgentPolicy, DecisionOutput
from agent_loop.policy.signature import ToolCall


class TestNormalizeToolCalls:
    def test_none(self):
        assert AgentPolicy._normalize_tool_calls(None) == []

    def test_empty_string(self):
        assert AgentPolicy._normalize_tool_calls("") == []

    def test_whitespace_string(self):
        assert AgentPolicy._normalize_tool_calls("   \n\t") == []

    def test_malformed_json(self):
        assert AgentPolicy._normalize_tool_calls("{not json") == []

    def test_single_dict_wrapped(self):
        calls = AgentPolicy._normalize_tool_calls({"name": "echo", "arguments": {"text": "hi"}})
        assert len(calls) == 1
        assert calls[0].name == "echo"
        assert calls[0].arguments == {"text": "hi"}

    def test_list_of_dicts(self):
        calls = AgentPolicy._normalize_tool_calls(
            [
                {"name": "a", "arguments": {"x": 1}},
                {"name": "b", "arguments": {}},
            ]
        )
        assert [c.name for c in calls] == ["a", "b"]

    def test_invalid_items_filtered(self):
        calls = AgentPolicy._normalize_tool_calls(
            [
                {"name": "a", "arguments": {}},
                "not a dict",
                {"missing_name": True},
                {"name": "b", "arguments": {"y": 2}},
            ]
        )
        assert [c.name for c in calls] == ["a", "b"]

    def test_already_toolcall_passthrough(self):
        existing = ToolCall(name="x", arguments={"k": 1})
        calls = AgentPolicy._normalize_tool_calls([existing])
        assert calls == [existing]

    def test_json_string_list(self):
        calls = AgentPolicy._normalize_tool_calls('[{"name":"echo","arguments":{"t":1}}]')
        assert len(calls) == 1
        assert calls[0].name == "echo"

    def test_non_list_non_dict_after_parse(self):
        assert AgentPolicy._normalize_tool_calls("42") == []


class TestDecisionOutput:
    def test_defaults(self):
        d = DecisionOutput(rationale="why", decision_type="final")
        assert d.tool_calls == []
        assert d.hitl_request == ""
        assert d.final_response == ""

    def test_repr_is_string(self):
        d = DecisionOutput(rationale="x" * 80, decision_type="tool")
        assert isinstance(repr(d), str)
        assert "tool" in repr(d)
