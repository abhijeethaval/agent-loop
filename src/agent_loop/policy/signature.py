"""DSPy signature for agent policy decisions.

This defines the Act signature that encodes policy precedence rules.
"""

from typing import Any, Literal

import dspy
from pydantic import BaseModel, Field

DecisionType = Literal["tool", "hitl", "final"]


class HistoryRecord(BaseModel):
    """Structured history entry provided to the policy."""

    step: int
    actor: Literal["agent", "tool", "human"]
    action: str
    arguments: dict[str, Any] | None = None
    outcome: Literal["success", "error", "feedback"]
    result: str


class ToolSpec(BaseModel):
    """Structured tool definition available to the policy."""

    name: str
    description: str


class ToolCall(BaseModel):
    """Structured tool call emitted by policy."""

    name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments object for the selected tool",
    )


class Act(dspy.Signature):
    """Decide the next action for the agent.

    You are a deterministic decision engine. Choose exactly one next action:
    'tool', 'hitl', or 'final'. Optimize for steady progress with the smallest
    safe useful step.

    Reasoning process (write this in rationale):
    1. Summarize relevant facts from user_messages and history.
    2. Apply policy precedence and constraints.
    3. Identify remaining gaps or blockers.
    4. Choose the best next action and briefly justify it.

    History discipline:
    - Treat history as the source of truth for what was already asked or tried.
    - Reuse prior HITL answers and tool outputs whenever possible.
    - Do not ask duplicate HITL questions.
    - Do not repeat the same failed tool call unless new information justifies it.

    Decision rules:
    - Use 'tool' when an available tool can make progress now.
    - Use 'hitl' only when progress is blocked by missing information that cannot
      be obtained from history or tools.
    - Use 'final' when the goal is achieved, or no further safe/useful progress
      can be made in this loop.

    Tool rules:
    - tool_calls must be a JSON array of objects:
      [{"name": "<tool_name>", "arguments": {...}}, ...]
    - Each tool name must match a tool in available_tools.
    - Each arguments object must include all required parameters with concrete values.
    - Pull argument values from history and prior tool results when available.
    - Use multiple tool_calls only when they are independent and safe to run concurrently.

    HITL rules:
    - Ask only for information required to unblock the next step.
    - Keep requests specific and non-redundant.

    Final response rules:
    - Give a complete user-facing response grounded in available evidence.
    - If unresolved, state what is missing and why stopping is appropriate.

    Policy precedence (highest to lowest):
    1. Organization policies
    2. Industry rules
    3. Domain guidelines
    4. User goal

    Output consistency:
    - decision_type must be exactly one of: 'tool', 'hitl', 'final'.
    - If decision_type='tool': tool_calls is required and must be non-empty.
      hitl_request and final_response must be empty.
    - If decision_type='hitl': hitl_request is required; tool_calls and final_response must be empty.
    - If decision_type='final': final_response is required; tool_calls and hitl_request must be empty.
    """
    
    # Input fields - State
    goal: str = dspy.InputField(desc="The goal the agent is trying to achieve")
    user_messages: list[str] = dspy.InputField(desc="Messages from the user")
    history: list[HistoryRecord] = dspy.InputField(
        desc="IMPORTANT: Contains previous actions including hitl_request (questions asked) and hitl_response (user answers). Check this before asking new questions!"
    )
    
    # Input fields - Policy Context
    org_policies: str = dspy.InputField(
        desc="Organization-level policies (highest priority)"
    )
    industry_rules: str = dspy.InputField(
        desc="Industry or regulatory rules"
    )
    domain_guidelines: str = dspy.InputField(
        desc="Domain-specific guidelines"
    )
    
    # Input fields - Available tools
    available_tools: list[ToolSpec] = dspy.InputField(
        desc="Structured tool definitions and parameter guidance"
    )
    
    # Output fields
    rationale: str = dspy.OutputField(
        desc="Step-by-step reasoning: facts from history, applied constraints, remaining gap, and chosen next action."
    )
    decision_type: DecisionType = dspy.OutputField(
        desc="Exactly one of: 'tool', 'hitl', 'final'."
    )
    tool_calls: list[ToolCall] = dspy.OutputField(
        desc='Tool calls to execute. Format: [{"name":"tool_name","arguments":{...}}]. Required and non-empty if decision_type is "tool"; otherwise []'
    )
    hitl_request: str = dspy.OutputField(
        desc="Concise request for missing user information needed to continue. Required if decision_type is 'hitl'; otherwise empty string."
    )
    final_response: str = dspy.OutputField(
        desc="Complete final response to the user. Required if decision_type is 'final'; otherwise empty string."
    )
    action_confirmation: str = dspy.OutputField(
        desc="Short confirmation of chosen action and expected outcome. Empty string if not applicable."
    )
