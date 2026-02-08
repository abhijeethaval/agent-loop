"""Main orchestrator implementing the agent loop.

The orchestrator owns state and controls the loop.
DSPy produces intent, not effects.
"""

from concurrent.futures import ThreadPoolExecutor
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
                available_tools=self._tools.get_tools_catalog(),
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
                if not decision.tool_calls:
                    result_message = "Policy selected 'tool' but provided no executable tool calls."
                    state.add_history_entry(
                        step=step,
                        actor="tool",
                        action="tool_batch",
                        arguments={},
                        outcome="error",
                        result=result_message,
                    )
                    self._audit.log_outcome(
                        step=step,
                        outcome_type="tool",
                        status="error",
                        result=result_message,
                        data={"tool_calls": []},
                    )
                    if self._console:
                        self._console.print(f"  [bold red]tool[/bold red]: {result_message}")
                    continue

                tool_results = self._execute_tool_calls_parallel(decision)
                has_error = any(result.status == "error" for _, _, result in tool_results)

                for tool_name, arguments, result in tool_results:
                    state.add_history_entry(
                        step=step,
                        actor="tool",
                        action=tool_name,
                        arguments=arguments,
                        outcome=result.status,
                        result=result.message,
                    )
                    if self._console:
                        self._print_tool_result(tool_name, result)

                self._audit.log_outcome(
                    step=step,
                    outcome_type="tool",
                    status="error" if has_error else "success",
                    result=(
                        f"Executed {len(tool_results)} tool call(s)."
                        if not has_error
                        else f"Executed {len(tool_results)} tool call(s) with at least one error."
                    ),
                    data={
                        "tool_calls": [
                            {
                                "name": tool_name,
                                "arguments": arguments,
                                "status": result.status,
                                "message": result.message,
                                "data": result.data,
                            }
                            for tool_name, arguments, result in tool_results
                        ]
                    },
                )
        
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
                "tool_calls": [
                    {"name": call.name, "arguments": call.arguments}
                    for call in decision.tool_calls
                ],
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
            if len(decision.tool_calls) == 1:
                call = decision.tool_calls[0]
                table.add_row("Tool", call.name)
                table.add_row("Arguments", str(call.arguments))
            elif len(decision.tool_calls) == 0:
                table.add_row("Tool Calls", "[]")
            else:
                calls_text = "\n".join(
                    f"{idx + 1}. {call.name} {call.arguments}"
                    for idx, call in enumerate(decision.tool_calls)
                )
                table.add_row("Tool Calls", calls_text)
        elif decision.decision_type == "hitl":
            table.add_row("HITL Request", decision.hitl_request)
        
        self._console.print(table)
    
    def _print_tool_result(self, tool: str, result: ToolResult) -> None:
        """Print tool execution result."""
        status_style = "green" if result.status == "success" else "red"
        self._console.print(
            f"  [bold {status_style}]{tool}[/bold {status_style}]: {result.message}"
        )

    def _execute_tool_calls_parallel(
        self,
        decision: DecisionOutput,
    ) -> list[tuple[str, dict[str, Any], ToolResult]]:
        """Execute requested tool calls concurrently, preserving decision order."""
        max_workers = max(1, min(len(decision.tool_calls), 8))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._tools.execute, call.name, call.arguments)
                for call in decision.tool_calls
            ]

            return [
                (call.name, call.arguments, future.result())
                for call, future in zip(decision.tool_calls, futures, strict=False)
            ]
    
    def _print_final(self, state: AgentState) -> None:
        """Print final response."""
        self._console.print()
        self._console.print(Panel(
            state.final_response or "No response",
            title="[bold green]Final Response[/bold green]",
            border_style="green",
        ))
