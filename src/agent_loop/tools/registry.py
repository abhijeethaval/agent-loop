"""Tool registry for managing and executing tools.

Tools are registered with the orchestrator and executed outside of DSPy.
"""

from typing import Any, Callable, Protocol

from agent_loop.models.tool_result import ToolResult


class ToolFunction(Protocol):
    """Protocol for tool functions."""
    
    def __call__(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments."""
        ...


class ToolRegistry:
    """Registry for managing tools.
    
    All tool execution happens outside DSPy.
    Errors are normalized before being added to history.
    """
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: dict[str, ToolFunction] = {}
        self._descriptions: dict[str, str] = {}
    
    def register(
        self,
        name: str,
        func: ToolFunction,
        description: str = "",
    ) -> None:
        """Register a tool with the registry.
        
        Args:
            name: Unique name for the tool
            func: Callable that takes kwargs and returns ToolResult
            description: Human-readable description for the LLM
        """
        self._tools[name] = func
        self._descriptions[name] = description
    
    def get(self, name: str) -> ToolFunction | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_tools_description(self) -> str:
        """Get a formatted description of all tools for the LLM."""
        if not self._tools:
            return "No tools available."
        
        lines = ["Available tools:"]
        for name, desc in self._descriptions.items():
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)
    
    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name with given arguments.
        
        All errors are caught and normalized into ToolResult.
        
        Args:
            name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            ToolResult with success/error status
        """
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.error(f"Tool '{name}' not found")
        
        try:
            result = tool(**arguments)
            # Ensure result is a ToolResult
            if not isinstance(result, ToolResult):
                return ToolResult.success(str(result))
            return result
        except TypeError as e:
            return ToolResult.error(f"Invalid arguments for '{name}': {e}")
        except Exception as e:
            return ToolResult.error(f"Tool '{name}' failed: {e}")
