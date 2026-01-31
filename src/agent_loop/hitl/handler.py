"""Human-in-the-Loop (HITL) handler.

HITL is a first-class decision outcome. Human input is treated as data, not instruction.
"""

from abc import ABC, abstractmethod
from typing import Callable

from rich.console import Console
from rich.panel import Panel


class HITLHandler(ABC):
    """Abstract base class for HITL handlers."""
    
    @abstractmethod
    def request_human_input(self, request: str) -> str:
        """Request input from a human.
        
        Args:
            request: Description of what input is needed
            
        Returns:
            Human-provided input string
        """
        ...


class ConsoleHITLHandler(HITLHandler):
    """HITL handler that uses console input/output."""
    
    def __init__(self):
        """Initialize console handler."""
        self._console = Console()
    
    def request_human_input(self, request: str) -> str:
        """Request input via console.
        
        Args:
            request: Description of what input is needed
            
        Returns:
            Human-provided input string
        """
        self._console.print()
        self._console.print(Panel(
            request,
            title="[bold yellow]Human Input Required[/bold yellow]",
            border_style="yellow",
        ))
        self._console.print()
        
        response = self._console.input("[bold green]Your response:[/bold green] ")
        return response


class CallbackHITLHandler(HITLHandler):
    """HITL handler that uses a callback function.
    
    Useful for programmatic integration (web apps, APIs, etc.)
    """
    
    def __init__(self, callback: Callable[[str], str]):
        """Initialize with a callback function.
        
        Args:
            callback: Function that takes request string and returns response
        """
        self._callback = callback
    
    def request_human_input(self, request: str) -> str:
        """Request input via callback.
        
        Args:
            request: Description of what input is needed
            
        Returns:
            Human-provided input string
        """
        return self._callback(request)


class AsyncHITLHandler(HITLHandler):
    """HITL handler for async workflows that queue requests.
    
    Useful for Temporal or similar workflow engines where the workflow
    needs to pause and resume.
    """
    
    def __init__(self):
        """Initialize async handler."""
        self._pending_request: str | None = None
        self._response: str | None = None
    
    @property
    def has_pending_request(self) -> bool:
        """Check if there's a pending HITL request."""
        return self._pending_request is not None
    
    @property
    def pending_request(self) -> str | None:
        """Get the pending request message."""
        return self._pending_request
    
    def request_human_input(self, request: str) -> str:
        """Queue request and raise to pause execution.
        
        Args:
            request: Description of what input is needed
            
        Raises:
            HITLPendingError: Always raises to signal workflow should pause
        """
        self._pending_request = request
        raise HITLPendingError(request)
    
    def provide_response(self, response: str) -> None:
        """Provide response to pending request.
        
        Args:
            response: Human-provided response
        """
        self._response = response
        self._pending_request = None
    
    def get_response(self) -> str:
        """Get the provided response."""
        if self._response is None:
            raise ValueError("No response has been provided")
        response = self._response
        self._response = None
        return response


class HITLPendingError(Exception):
    """Raised when HITL input is needed and workflow should pause."""
    
    def __init__(self, request: str):
        self.request = request
        super().__init__(f"HITL input required: {request}")
