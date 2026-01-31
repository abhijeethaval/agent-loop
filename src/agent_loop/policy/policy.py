"""Agent policy module using DSPy.

DSPy is used only for decision-making. It never executes tools.
"""

import json
from typing import Any

import dspy

from agent_loop.policy.signature import Act


class DecisionOutput:
    """Structured decision output from policy."""
    
    def __init__(
        self,
        rationale: str,
        decision_type: str,
        selected_tool: str = "",
        arguments: dict[str, Any] | None = None,
        hitl_request: str = "",
        final_response: str = "",
    ):
        self.rationale = rationale
        self.decision_type = decision_type
        self.selected_tool = selected_tool
        self.arguments = arguments or {}
        self.hitl_request = hitl_request
        self.final_response = final_response
    
    def __repr__(self) -> str:
        return (
            f"DecisionOutput(type={self.decision_type!r}, "
            f"tool={self.selected_tool!r}, rationale={self.rationale[:50]!r}...)"
        )


class AgentPolicy:
    """Policy module wrapping DSPy ChainOfThought.
    
    Produces intent, not effects. DSPy never owns memory or state.
    """
    
    def __init__(self):
        """Initialize the policy with ChainOfThought reasoning."""
        self._policy = dspy.ChainOfThought(Act)
    
    def decide(
        self,
        goal: str,
        user_messages: list[str],
        history: list[dict],
        org_policies: str,
        industry_rules: str,
        domain_guidelines: str,
        available_tools: str,
    ) -> DecisionOutput:
        """Make a decision based on current state and policies.
        
        Args:
            goal: The goal the agent is trying to achieve
            user_messages: Messages from the user
            history: History of actions and outcomes
            org_policies: Organization-level policies
            industry_rules: Industry or regulatory rules
            domain_guidelines: Domain-specific guidelines
            available_tools: Description of available tools
            
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
        
        # Parse arguments from JSON string
        arguments = {}
        if result.arguments and result.arguments.strip():
            try:
                arguments = json.loads(result.arguments)
            except json.JSONDecodeError:
                # If parsing fails, treat as empty arguments
                arguments = {}
        
        # Normalize decision type
        decision_type = result.decision_type.lower().strip()
        if decision_type not in ("tool", "hitl", "final"):
            # Default to final if unrecognized
            decision_type = "final"
        
        return DecisionOutput(
            rationale=result.rationale,
            decision_type=decision_type,
            selected_tool=result.selected_tool if decision_type == "tool" else "",
            arguments=arguments if decision_type == "tool" else {},
            hitl_request=result.hitl_request if decision_type == "hitl" else "",
            final_response=result.final_response if decision_type == "final" else "",
        )
