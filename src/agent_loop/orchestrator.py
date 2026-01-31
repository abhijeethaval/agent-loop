"""Main orchestrator implementing the agent loop.

The orchestrator owns state and controls the loop.
DSPy produces intent, not effects.
"""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_loop.audit.logger import AuditLogger
from agent_loop.hitl.handler import HITLHandler, ConsoleHITLHandler
from agent_loop.models.policy_context import PolicyContext
from agent_loop.models.state import AgentState
from agent_loop.models.tool_result import ToolResult
from agent_loop.policy.policy import AgentPolicy, DecisionOutput
from agent_loop.streaming.streamer import StreamHandler, NullStreamHandler, StreamingConfig
from agent_loop.tools.registry import ToolRegistry


class OrchestratorConfig:
    """Configuration for the orchestrator."""
    
    def __init__(
        self,
        max_steps: int = 50,
        verbose: bool = True,
        audit_dir: Path | str | None = None,
        streaming: StreamingConfig | None = None,
    ):
        """Initialize orchestrator configuration.
        
        Args:
            max_steps: Maximum number of steps before forced termination
            verbose: Whether to print progress to console
            audit_dir: Directory for audit logs
            streaming: Streaming configuration
        """
        self.max_steps = max_steps
        self.verbose = verbose
        self.audit_dir = Path(audit_dir) if audit_dir else None
        self.streaming = streaming or StreamingConfig(enabled=False)


class Orchestrator:
    """Main agent loop orchestrator.
    
    Implements the authoritative flow from the specification.
    All state is explicit and replayable.
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        hitl_handler: HITLHandler | None = None,
        stream_handler: StreamHandler | None = None,
        config: OrchestratorConfig | None = None,
    ):
        """Initialize the orchestrator.
        
        Args:
            tool_registry: Registry of available tools
            hitl_handler: Handler for human-in-the-loop requests
            stream_handler: Handler for streaming output
            config: Orchestrator configuration
        """
        self._policy = AgentPolicy()
        self._tools = tool_registry or ToolRegistry()
        self._hitl = hitl_handler or ConsoleHITLHandler()
        self._stream = stream_handler or NullStreamHandler()
        self._config = config or OrchestratorConfig()
        self._console = Console() if self._config.verbose else None
        self._audit = AuditLogger(log_dir=self._config.audit_dir)
    
    @property
    def audit_logger(self) -> AuditLogger:
        """Get the audit logger."""
        return self._audit
    
    def run(
        self,
        state: AgentState,
        policy_context: PolicyContext,
    ) -> AgentState:
        """Run the agent loop until completion.
        
        This is the authoritative flow from the specification.
        
        Args:
            state: Initial agent state
            policy_context: Policy context for decision making
            
        Returns:
            Final agent state with response
        """
        step = 0
        
        if self._console:
            self._print_start(state, policy_context)
        
        while step < self._config.max_steps:
            # Get decision from policy (DSPy)
            decision = self._policy.decide(
                goal=state.goal,
                user_messages=state.user_messages,
                history=state.get_history_dicts(),
                org_policies=policy_context.org_policies,
                industry_rules=policy_context.industry_rules,
                domain_guidelines=policy_context.domain_guidelines,
                available_tools=self._tools.get_tools_description(),
            )
            
            # Log decision to audit
            self._audit.log_decision(
                step=step,
                goal=state.goal,
                history=state.get_history_dicts(),
                policy_context={
                    "org_policies": policy_context.org_policies,
                    "industry_rules": policy_context.industry_rules,
                    "domain_guidelines": policy_context.domain_guidelines,
                },
                decision_type=decision.decision_type,
                decision_details=self._get_decision_details(decision),
                rationale=decision.rationale,
            )
            
            if self._console:
                self._print_decision(step, decision)
            
            # Handle final response
            if decision.decision_type == "final":
                state.final_response = decision.final_response
                self._stream.on_complete(decision.final_response)
                
                if self._console:
                    self._print_final(state)
                break
            
            # Handle HITL request
            if decision.decision_type == "hitl":
                # First, record the agent's question in history
                state.add_history_entry(
                    step=step,
                    actor="agent",
                    action="hitl_request",
                    outcome="success",
                    result=decision.hitl_request,
                )
                
                # Get human input
                human_input = self._hitl.request_human_input(decision.hitl_request)
                
                # Record human's response in history
                state.add_history_entry(
                    step=step,
                    actor="human",
                    action="hitl_response",
                    outcome="feedback",
                    result=human_input,
                )
                
                self._audit.log_outcome(
                    step=step,
                    outcome_type="hitl",
                    status="feedback",
                    result=human_input,
                )
                
                # Increment step after HITL so LLM sees progress
                step += 1
                continue
            
            # Handle tool execution
            if decision.decision_type == "tool":
                step += 1
                result = self._tools.execute(
                    decision.selected_tool,
                    decision.arguments,
                )
                
                state.add_history_entry(
                    step=step,
                    actor="tool",
                    action=decision.selected_tool,
                    arguments=decision.arguments,
                    outcome=result.status,
                    result=result.message,
                )
                
                self._audit.log_outcome(
                    step=step,
                    outcome_type="tool",
                    status=result.status,
                    result=result.message,
                    data=result.data,
                )
                
                if self._console:
                    self._print_tool_result(decision.selected_tool, result)
        
        else:
            # Max steps reached
            state.final_response = (
                f"Agent terminated after {self._config.max_steps} steps "
                "without reaching a final response."
            )
            if self._console:
                self._console.print(
                    f"[bold red]Max steps ({self._config.max_steps}) reached[/bold red]"
                )
        
        return state
    
    def _get_decision_details(self, decision: DecisionOutput) -> dict[str, Any]:
        """Extract decision-specific details for logging."""
        if decision.decision_type == "tool":
            return {
                "selected_tool": decision.selected_tool,
                "arguments": decision.arguments,
            }
        elif decision.decision_type == "hitl":
            return {"hitl_request": decision.hitl_request}
        elif decision.decision_type == "final":
            return {"final_response": decision.final_response}
        return {}
    
    def _print_start(self, state: AgentState, ctx: PolicyContext) -> None:
        """Print start of agent run."""
        self._console.print()
        self._console.print(Panel(
            f"[bold]Goal:[/bold] {state.goal}\n"
            f"[bold]Messages:[/bold] {len(state.user_messages)}\n"
            f"[bold]History:[/bold] {len(state.history)} entries",
            title="[bold blue]Agent Starting[/bold blue]",
            border_style="blue",
        ))
    
    def _print_decision(self, step: int, decision: DecisionOutput) -> None:
        """Print decision info."""
        table = Table(title=f"Step {step} Decision", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        table.add_row("Type", f"[bold]{decision.decision_type}[/bold]")
        table.add_row("Rationale", decision.rationale[:100] + "..." 
                      if len(decision.rationale) > 100 else decision.rationale)
        
        if decision.decision_type == "tool":
            table.add_row("Tool", decision.selected_tool)
            table.add_row("Arguments", str(decision.arguments))
        elif decision.decision_type == "hitl":
            table.add_row("HITL Request", decision.hitl_request)
        
        self._console.print(table)
    
    def _print_tool_result(self, tool: str, result: ToolResult) -> None:
        """Print tool execution result."""
        status_style = "green" if result.status == "success" else "red"
        self._console.print(
            f"  [bold {status_style}]{tool}[/bold {status_style}]: {result.message}"
        )
    
    def _print_final(self, state: AgentState) -> None:
        """Print final response."""
        self._console.print()
        self._console.print(Panel(
            state.final_response or "No response",
            title="[bold green]Final Response[/bold green]",
            border_style="green",
        ))
