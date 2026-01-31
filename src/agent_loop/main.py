"""Main CLI entry point for the agent loop."""

import argparse
import os
import warnings
from pathlib import Path

# Suppress Pydantic serialization warnings from litellm/dspy internals
warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings:",
    category=UserWarning,
    module="pydantic",
)

import dspy
from dotenv import load_dotenv

from agent_loop.models.policy_context import PolicyContext
from agent_loop.models.state import AgentState
from agent_loop.orchestrator import Orchestrator, OrchestratorConfig
from agent_loop.tools.example_tools import create_default_registry


def configure_lm(provider: str = "openai", model: str | None = None) -> None:
    """Configure the DSPy language model.
    
    Args:
        provider: LLM provider (openai, anthropic, etc.)
        model: Model name (defaults vary by provider)
    """
    load_dotenv()
    
    if provider == "openai":
        model = model or "gpt-4o-mini"
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        lm = dspy.LM(f"openai/{model}", api_key=api_key)
    elif provider == "anthropic":
        model = model or "claude-3-5-sonnet-20241022"
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        lm = dspy.LM(f"anthropic/{model}", api_key=api_key)
    elif provider == "dummy":
        # For testing without API keys
        lm = dspy.LM("openai/gpt-3.5-turbo", api_key="dummy")
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    dspy.configure(lm=lm)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the DSPy agentic loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "goal",
        type=str,
        help="Goal for the agent to achieve",
    )
    parser.add_argument(
        "-m", "--message",
        type=str,
        action="append",
        default=[],
        help="User message(s) to include",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic", "dummy"],
        help="LLM provider to use",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name (defaults vary by provider)",
    )
    parser.add_argument(
        "--org-policies",
        type=str,
        default="",
        help="Organization policies to apply",
    )
    parser.add_argument(
        "--industry-rules",
        type=str,
        default="",
        help="Industry/regulatory rules to apply",
    )
    parser.add_argument(
        "--domain-guidelines",
        type=str,
        default="",
        help="Domain-specific guidelines",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum number of steps",
    )
    parser.add_argument(
        "--audit-dir",
        type=str,
        default=None,
        help="Directory for audit logs",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    
    args = parser.parse_args()
    
    # Configure LM
    configure_lm(provider=args.provider, model=args.model)
    
    # Create state and context
    state = AgentState(
        goal=args.goal,
        user_messages=args.message,
    )
    policy_ctx = PolicyContext(
        org_policies=args.org_policies,
        industry_rules=args.industry_rules,
        domain_guidelines=args.domain_guidelines,
    )
    
    # Create orchestrator
    config = OrchestratorConfig(
        max_steps=args.max_steps,
        verbose=not args.quiet,
        audit_dir=Path(args.audit_dir) if args.audit_dir else None,
    )
    orchestrator = Orchestrator(
        tool_registry=create_default_registry(),
        config=config,
    )
    
    # Run the agent
    result = orchestrator.run(state, policy_ctx)
    
    # Print final response if quiet mode
    if args.quiet and result.final_response:
        print(result.final_response)


if __name__ == "__main__":
    main()
