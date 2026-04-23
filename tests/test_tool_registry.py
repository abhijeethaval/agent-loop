"""Tests for ToolRegistry."""

from __future__ import annotations

from agent_loop.models.tool_result import ToolResult
from agent_loop.tools.registry import ToolRegistry


def _ok_tool(text: str) -> ToolResult:
    return ToolResult.success(f"got:{text}")


def _raising_tool(**_: object) -> ToolResult:
    raise RuntimeError("kaboom")


def _non_toolresult_tool(**_: object):
    return 42


class TestRegistration:
    def test_register_and_get(self):
        r = ToolRegistry()
        r.register("ok", _ok_tool, "echoer")
        assert r.get("ok") is _ok_tool
        assert r.get("missing") is None

    def test_list_tools(self):
        r = ToolRegistry()
        r.register("a", _ok_tool)
        r.register("b", _ok_tool)
        assert set(r.list_tools()) == {"a", "b"}

    def test_empty_tools_description(self):
        assert ToolRegistry().get_tools_description() == "No tools available."

    def test_tools_description_lists_entries(self):
        r = ToolRegistry()
        r.register("ok", _ok_tool, "echoer")
        desc = r.get_tools_description()
        assert "ok" in desc
        assert "echoer" in desc

    def test_tools_catalog_shape(self):
        r = ToolRegistry()
        r.register("ok", _ok_tool, "echoer")
        catalog = r.get_tools_catalog()
        assert catalog == [{"name": "ok", "description": "echoer"}]


class TestExecute:
    def test_missing_tool_returns_error(self):
        r = ToolRegistry()
        result = r.execute("nope", {})
        assert result.status == "error"
        assert "not found" in result.message

    def test_happy_path(self):
        r = ToolRegistry()
        r.register("ok", _ok_tool)
        result = r.execute("ok", {"text": "hi"})
        assert result.status == "success"
        assert result.message == "got:hi"

    def test_bad_arguments_returns_type_error(self):
        r = ToolRegistry()
        r.register("ok", _ok_tool)
        result = r.execute("ok", {"wrong": "kw"})
        assert result.status == "error"
        assert "Invalid arguments" in result.message

    def test_arbitrary_exception_normalized(self):
        r = ToolRegistry()
        r.register("boom", _raising_tool)
        result = r.execute("boom", {})
        assert result.status == "error"
        assert "failed" in result.message
        assert "kaboom" in result.message

    def test_non_toolresult_return_wrapped(self):
        r = ToolRegistry()
        r.register("raw", _non_toolresult_tool)
        result = r.execute("raw", {})
        assert result.status == "success"
        assert result.message == "42"
