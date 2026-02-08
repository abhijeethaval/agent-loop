"""Agent policy module using DSPy.

DSPy is used only for decision-making. It never executes tools.
"""

import json
from typing import Any, cast

import dspy

from agent_loop.policy.signature import Act, DecisionType, HistoryRecord, ToolCall, ToolSpec


class DecisionOutput:
    """Structured decision output from policy."""
    
    def __init__(
        self,
        rationale: str,
        decision_type: DecisionType,
        tool_calls: list[ToolCall] | None = None,
        hitl_request: str = "",
        final_response: str = "",
    ):
        self.rationale = rationale
        self.decision_type = decision_type
        self.tool_calls = tool_calls or []
        self.hitl_request = hitl_request
        self.final_response = final_response
    
    def __repr__(self) -> str:
        return (
            f"DecisionOutput(type={self.decision_type!r}, "
            f"tool_calls={len(self.tool_calls)!r}, rationale={self.rationale[:50]!r}...)"
        )


class AgentPolicy:
    """Policy module wrapping DSPy ChainOfThought.
    
    Produces intent, not effects. DSPy never owns memory or state.
    """
    
    def __init__(self):
        """Initialize the policy with ChainOfThought reasoning."""
        self._policy = dspy.ChainOfThought(Act)

    @staticmethod
    def _normalize_tool_calls(raw_tool_calls: Any) -> list[ToolCall]:
        """Normalize tool_calls into a validated list."""
        if raw_tool_calls is None:
            return []

        parsed = raw_tool_calls
        if isinstance(raw_tool_calls, str):
            if not raw_tool_calls.strip():
                return []
            try:
                parsed = json.loads(raw_tool_calls)
            except json.JSONDecodeError:
                return []

        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return []

        normalized: list[ToolCall] = []
        for item in parsed:
            if isinstance(item, ToolCall):
                normalized.append(item)
                continue
            if not isinstance(item, dict):
                continue
            try:
                normalized.append(ToolCall.model_validate(item))
            except Exception:
                continue

        return normalized
    
    def decide(
        self,
        goal: str,
        user_messages: list[str],
        history: list[dict[str, Any]] | list[HistoryRecord],
        org_policies: str,
        industry_rules: str,
        domain_guidelines: str,
        available_tools: list[dict[str, str]] | list[ToolSpec],
    ) -> DecisionOutput:
        """Make a decision based on current state and policies.
        
        Args:
            goal: The goal the agent is trying to achieve
            user_messages: Messages from the user
            history: History of actions and outcomes
            org_policies: Organization-level policies
            industry_rules: Industry or regulatory rules
            domain_guidelines: Domain-specific guidelines
            available_tools: Structured list of available tools
            
        Returns:
            DecisionOutput with the policy's decision
        """
        result = self._policy(
            goal=goal,
            user_messages=user_messages,
            history=history,
            org_policies=org_policies,
            industry_rules=industry_rules,
            domain_guidelines=domain_guidelines,
            available_tools=available_tools,
        )

        tool_calls = self._normalize_tool_calls(result.tool_calls)

        # Normalize decision type
        decision_type = (
            result.decision_type.lower().strip()
            if isinstance(result.decision_type, str)
            else "final"
        )
        if decision_type not in ("tool", "hitl", "final"):
            # Default to final if unrecognized
            decision_type = "final"

        if decision_type != "tool":
            tool_calls = []

        normalized_decision_type = cast(DecisionType, decision_type)
        
        return DecisionOutput(
            rationale=result.rationale,
            decision_type=normalized_decision_type,
            tool_calls=tool_calls,
            hitl_request=result.hitl_request if normalized_decision_type == "hitl" else "",
            final_response=result.final_response if normalized_decision_type == "final" else "",
        )
