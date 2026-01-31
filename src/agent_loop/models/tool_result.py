"""Tool result model.

Defines the standardized result schema for tool execution.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standardized tool execution result.
    
    All errors must be normalized before being added to history.
    """
    status: Literal["success", "error"] = Field(
        ...,
        description="Whether the tool execution succeeded or failed"
    )
    message: str = Field(
        ...,
        description="Human-readable result or error message"
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured data returned by the tool"
    )

    @classmethod
    def success(cls, message: str, data: dict[str, Any] | None = None) -> "ToolResult":
        """Create a successful tool result."""
        return cls(status="success", message=message, data=data)

    @classmethod
    def error(cls, message: str, data: dict[str, Any] | None = None) -> "ToolResult":
        """Create an error tool result."""
        return cls(status="error", message=message, data=data)
