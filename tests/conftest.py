"""Shared fixtures for the agent-loop test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from agent_loop.models.tool_result import ToolResult
from agent_loop.policy.policy import DecisionOutput
from agent_loop.tools.registry import ToolRegistry


@pytest.fixture
def tmp_audit_dir(tmp_path: Path) -> Path:
    return tmp_path / "audit_logs"


class ScriptedPolicy:
    """Deterministic stand-in for AgentPolicy used by orchestrator tests."""

    def __init__(self, decisions: list[DecisionOutput]):
        self._decisions = list(decisions)
        self.calls: list[dict] = []

    def decide(self, **kwargs) -> DecisionOutput:
        self.calls.append(kwargs)
        if not self._decisions:
            raise AssertionError(
                "ScriptedPolicy ran out of decisions; orchestrator made more calls than scripted."
            )
        return self._decisions.pop(0)


@pytest.fixture
def scripted_policy() -> type[ScriptedPolicy]:
    return ScriptedPolicy


@pytest.fixture
def simple_registry() -> ToolRegistry:
    """Registry with deterministic fake tools."""
    registry = ToolRegistry()

    def echo(text: str = "") -> ToolResult:
        return ToolResult.success(message=f"echo:{text}", data={"text": text})

    def adder(a: int = 0, b: int = 0) -> ToolResult:
        return ToolResult.success(message=f"sum={a + b}", data={"sum": a + b})

    def boom() -> ToolResult:
        raise RuntimeError("boom")

    registry.register("echo", echo, "Echo the provided text.")
    registry.register("adder", adder, "Add two integers.")
    registry.register("boom", boom, "Always raises.")
    return registry


@pytest.fixture(autouse=True)
def _no_dspy_lm(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure no accidental DSPy LM configuration leaks across tests."""
    yield
