"""Tests for the Orchestrator loop with a scripted policy."""

from __future__ import annotations

from agent_loop.hitl.handler import CallbackHITLHandler
from agent_loop.models.policy_context import PolicyContext
from agent_loop.models.state import AgentState
from agent_loop.orchestrator import Orchestrator, OrchestratorConfig
from agent_loop.policy.policy import DecisionOutput
from agent_loop.policy.signature import ToolCall


def _build(orch_kwargs: dict | None = None, config_kwargs: dict | None = None):
    config = OrchestratorConfig(verbose=False, **(config_kwargs or {}))
    orch = Orchestrator(config=config, **(orch_kwargs or {}))
    return orch


def _run(orch: Orchestrator, state: AgentState | None = None):
    state = state or AgentState(goal="g")
    ctx = PolicyContext()
    return orch.run(state, ctx)


class TestFinalDecision:
    def test_final_sets_response_and_exits(self, scripted_policy):
        orch = _build()
        orch._policy = scripted_policy(
            [DecisionOutput(rationale="done", decision_type="final", final_response="bye")]
        )
        state = _run(orch)
        assert state.final_response == "bye"
        assert len(state.history) == 0


class TestToolDecision:
    def test_tool_then_final(self, scripted_policy, simple_registry):
        orch = _build({"tool_registry": simple_registry})
        orch._policy = scripted_policy(
            [
                DecisionOutput(
                    rationale="call echo",
                    decision_type="tool",
                    tool_calls=[ToolCall(name="echo", arguments={"text": "hi"})],
                ),
                DecisionOutput(rationale="done", decision_type="final", final_response="ok"),
            ]
        )
        state = _run(orch)
        assert state.final_response == "ok"
        assert len(state.history) == 1
        entry = state.history[0]
        assert entry.actor == "tool"
        assert entry.action == "echo"
        assert entry.outcome == "success"
        assert entry.result == "echo:hi"
        assert entry.arguments == {"text": "hi"}

    def test_tool_decision_with_no_calls_records_error(self, scripted_policy):
        orch = _build()
        orch._policy = scripted_policy(
            [
                DecisionOutput(rationale="oops", decision_type="tool", tool_calls=[]),
                DecisionOutput(rationale="done", decision_type="final", final_response="fin"),
            ]
        )
        state = _run(orch)
        assert state.final_response == "fin"
        assert len(state.history) == 1
        entry = state.history[0]
        assert entry.outcome == "error"
        assert "no executable tool calls" in entry.result

    def test_tool_error_is_normalized(self, scripted_policy, simple_registry):
        orch = _build({"tool_registry": simple_registry})
        orch._policy = scripted_policy(
            [
                DecisionOutput(
                    rationale="try boom",
                    decision_type="tool",
                    tool_calls=[ToolCall(name="boom", arguments={})],
                ),
                DecisionOutput(rationale="done", decision_type="final", final_response="end"),
            ]
        )
        state = _run(orch)
        assert len(state.history) == 1
        assert state.history[0].outcome == "error"

    def test_parallel_tool_calls_preserve_order(self, scripted_policy, simple_registry):
        orch = _build({"tool_registry": simple_registry})
        orch._policy = scripted_policy(
            [
                DecisionOutput(
                    rationale="batch",
                    decision_type="tool",
                    tool_calls=[
                        ToolCall(name="echo", arguments={"text": "first"}),
                        ToolCall(name="adder", arguments={"a": 2, "b": 3}),
                        ToolCall(name="echo", arguments={"text": "third"}),
                    ],
                ),
                DecisionOutput(rationale="done", decision_type="final", final_response="fin"),
            ]
        )
        state = _run(orch)
        assert [h.action for h in state.history] == ["echo", "adder", "echo"]
        assert state.history[0].result == "echo:first"
        assert state.history[1].result == "sum=5"
        assert state.history[2].result == "echo:third"


class TestHITLDecision:
    def test_hitl_records_agent_and_human(self, scripted_policy):
        captured: list[str] = []

        def respond(request: str) -> str:
            captured.append(request)
            return "human-says-ok"

        orch = _build({"hitl_handler": CallbackHITLHandler(respond)})
        orch._policy = scripted_policy(
            [
                DecisionOutput(
                    rationale="need info",
                    decision_type="hitl",
                    hitl_request="What is your name?",
                ),
                DecisionOutput(rationale="done", decision_type="final", final_response="hello"),
            ]
        )
        state = _run(orch)
        assert state.final_response == "hello"
        assert captured == ["What is your name?"]
        assert len(state.history) == 2
        agent_entry, human_entry = state.history
        assert agent_entry.actor == "agent"
        assert agent_entry.action == "hitl_request"
        assert agent_entry.result == "What is your name?"
        assert human_entry.actor == "human"
        assert human_entry.action == "hitl_response"
        assert human_entry.outcome == "feedback"
        assert human_entry.result == "human-says-ok"


class TestMaxSteps:
    def test_terminates_after_max_steps(self, scripted_policy, simple_registry):
        # Always return a tool decision so the loop never reaches 'final'.
        decisions = [
            DecisionOutput(
                rationale="keep going",
                decision_type="tool",
                tool_calls=[ToolCall(name="echo", arguments={"text": "x"})],
            )
            for _ in range(10)
        ]
        orch = _build(
            orch_kwargs={"tool_registry": simple_registry},
            config_kwargs={"max_steps": 3},
        )
        orch._policy = scripted_policy(decisions)
        state = _run(orch)
        assert state.final_response is not None
        assert "terminated after 3 steps" in state.final_response
