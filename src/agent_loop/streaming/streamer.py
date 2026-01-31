"""Streaming support for agent responses.

Streaming is orthogonal to reasoning. It applies to text output only.
Streaming is a transport concern, not a policy concern.
"""

from abc import ABC, abstractmethod
from typing import Callable

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown


class StreamHandler(ABC):
    """Abstract base class for stream handlers."""
    
    @abstractmethod
    def on_token(self, token: str) -> None:
        """Handle a single streamed token.
        
        Args:
            token: The token string
        """
        ...
    
    @abstractmethod
    def on_complete(self, full_text: str) -> None:
        """Called when streaming is complete.
        
        Args:
            full_text: The complete streamed text
        """
        ...


class ConsoleStreamHandler(StreamHandler):
    """Stream handler that outputs to console."""
    
    def __init__(self, use_markdown: bool = True):
        """Initialize console stream handler.
        
        Args:
            use_markdown: Whether to render as markdown
        """
        self._console = Console()
        self._use_markdown = use_markdown
        self._buffer = ""
    
    def on_token(self, token: str) -> None:
        """Print token to console.
        
        Args:
            token: The token string
        """
        self._buffer += token
        # Print without newline for streaming effect
        self._console.print(token, end="")
    
    def on_complete(self, full_text: str) -> None:
        """Finalize output.
        
        Args:
            full_text: The complete text
        """
        self._console.print()  # New line
        self._buffer = ""


class BufferedStreamHandler(StreamHandler):
    """Stream handler that collects tokens into a buffer."""
    
    def __init__(self, token_callback: Callable[[str], None] | None = None):
        """Initialize buffered stream handler.
        
        Args:
            token_callback: Optional callback for each token
        """
        self._buffer = ""
        self._token_callback = token_callback
    
    @property
    def text(self) -> str:
        """Get the current buffered text."""
        return self._buffer
    
    def on_token(self, token: str) -> None:
        """Buffer token.
        
        Args:
            token: The token string
        """
        self._buffer += token
        if self._token_callback:
            self._token_callback(token)
    
    def on_complete(self, full_text: str) -> None:
        """Mark streaming complete.
        
        Args:
            full_text: The complete text
        """
        self._buffer = full_text
    
    def reset(self) -> None:
        """Reset the buffer."""
        self._buffer = ""


class NullStreamHandler(StreamHandler):
    """No-op stream handler for when streaming is not needed."""
    
    def on_token(self, token: str) -> None:
        """Do nothing."""
        pass
    
    def on_complete(self, full_text: str) -> None:
        """Do nothing."""
        pass


class StreamingConfig:
    """Configuration for streaming behavior."""
    
    def __init__(
        self,
        enabled: bool = True,
        stream_rationale: bool = False,
        stream_hitl_request: bool = True,
        stream_final_response: bool = True,
    ):
        """Initialize streaming configuration.
        
        Args:
            enabled: Master switch for streaming
            stream_rationale: Whether to stream rationale
            stream_hitl_request: Whether to stream HITL requests
            stream_final_response: Whether to stream final responses
        """
        self.enabled = enabled
        self.stream_rationale = stream_rationale
        self.stream_hitl_request = stream_hitl_request
        self.stream_final_response = stream_final_response
