"""Agent state model.

Defines the core state structures owned by the orchestrator.
History grows monotonically and never contains policies or instructions.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class HistoryEntry(BaseModel):
    """A single entry in the agent's history.
    
    History contains facts, not instructions.
    """
    step: int = Field(..., description="Step number in the agent loop")
    actor: Literal["agent", "tool", "human"] = Field(
        ..., 
        description="Who performed the action"
    )
    action: str = Field(..., description="The action taken")
    arguments: dict[str, Any] | None = Field(
        default=None, 
        description="Arguments for the action"
    )
    outcome: Literal["success", "error", "feedback"] = Field(
        ..., 
        description="Result status of the action"
    )
    result: str = Field(..., description="Result message or data")


class AgentState(BaseModel):
    """Agent state owned by the orchestrator.
    
    All state is explicit and replayable.
    """
    goal: str = Field(..., description="The goal the agent is trying to achieve")
    user_messages: list[str] = Field(
        default_factory=list,
        description="Messages from the user"
    )
    history: list[HistoryEntry] = Field(
        default_factory=list,
        description="History of actions and outcomes"
    )
    final_response: str | None = Field(
        default=None,
        description="Final response when agent completes"
    )

    def add_history_entry(
        self,
        step: int,
        actor: Literal["agent", "tool", "human"],
        action: str,
        outcome: Literal["success", "error", "feedback"],
        result: str,
        arguments: dict[str, Any] | None = None,
    ) -> None:
        """Append a history entry to the state."""
        entry = HistoryEntry(
            step=step,
            actor=actor,
            action=action,
            arguments=arguments,
            outcome=outcome,
            result=result,
        )
        self.history.append(entry)

    def get_history_dicts(self) -> list[dict[str, Any]]:
        """Get history as a list of dicts for DSPy consumption."""
        return [entry.model_dump() for entry in self.history]
