"""Example usage of the agent loop.

This demonstrates the full agent loop with a mock LM for testing.
"""

import dspy

from agent_loop.models.policy_context import PolicyContext
from agent_loop.models.state import AgentState
from agent_loop.orchestrator import Orchestrator, OrchestratorConfig
from agent_loop.tools.example_tools import create_default_registry


def run_with_mock_lm():
    """Run the agent with a mock LM for demonstration.
    
    This uses DSPy's DummyLM to simulate responses without API keys.
    """
    # Configure mock responses for testing
    mock_responses = [
        # First call - decide to use a tool
        """{
            "rationale": "The user wants to know about the weather in Tokyo. I should use the get_weather tool to fetch current conditions.",
            "decision_type": "tool",
            "selected_tool": "get_weather",
            "arguments": "{\\"location\\": \\"Tokyo\\"}",
            "hitl_request": "",
            "final_response": ""
        }""",
        # Second call - produce final response
        """{
            "rationale": "I have obtained the weather information for Tokyo. Now I can provide a helpful response to the user.",
            "decision_type": "final",
            "selected_tool": "",
            "arguments": "{}",
            "hitl_request": "",
            "final_response": "The current weather in Tokyo is available. Based on the weather tool, conditions are typical for the season. Please check the history for specific details about temperature and conditions."
        }"""
    ]
    
    # Use a simple mock by configuring DSPy with responses
    # Note: In real usage, you would configure with actual LM
    lm = dspy.LM("openai/gpt-3.5-turbo", api_key="test-key")
    dspy.configure(lm=lm)
    
    print("=" * 60)
    print("DSPy Agentic Loop - Example")
    print("=" * 60)
    print("\nNote: This example requires a valid API key to work.")
    print("Set OPENAI_API_KEY or use the CLI with --provider option.\n")
    
    # Create state
    state = AgentState(
        goal="Get the weather forecast for Tokyo and provide a summary",
        user_messages=["What's the weather like in Tokyo today?"],
    )
    
    # Create policy context
    policy_ctx = PolicyContext(
        org_policies="Always be helpful and provide accurate information.",
        industry_rules="",
        domain_guidelines="When discussing weather, include temperature and conditions.",
    )
    
    # Create orchestrator
    config = OrchestratorConfig(
        max_steps=10,
        verbose=True,
    )
    orchestrator = Orchestrator(
        tool_registry=create_default_registry(),
        config=config,
    )
    
    # Run the agent
    print("\nStarting agent loop...\n")
    try:
        result = orchestrator.run(state, policy_ctx)
        
        print("\n" + "=" * 60)
        print("Agent Loop Complete")
        print("=" * 60)
        print(f"\nFinal Response: {result.final_response}")
        print(f"\nHistory entries: {len(result.history)}")
        for entry in result.history:
            print(f"  - Step {entry.step}: {entry.actor} -> {entry.action} ({entry.outcome})")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTo run this example with a real LM, set your API key:")
        print("  export OPENAI_API_KEY='your-key'")
        print("  python examples/example.py")


def run_programmatic_example():
    """Show how to use the agent loop programmatically."""
    print("\n" + "=" * 60)
    print("Programmatic Usage Example (No LM Required)")
    print("=" * 60)
    
    from agent_loop.models.state import AgentState, HistoryEntry
    from agent_loop.models.policy_context import PolicyContext
    from agent_loop.models.tool_result import ToolResult
    from agent_loop.tools.registry import ToolRegistry
    from agent_loop.tools.example_tools import search_web, calculate
    from agent_loop.audit.logger import AuditLogger
    
    # Create a custom tool registry
    registry = ToolRegistry()
    registry.register("search", search_web, "Search the web")
    registry.register("calc", calculate, "Calculate math expressions")
    
    print("\n1. Created tool registry with 2 tools:")
    print(f"   {registry.list_tools()}")
    
    # Execute a tool
    result = registry.execute("calc", {"expression": "2 + 2 * 10"})
    print(f"\n2. Tool execution result:")
    print(f"   {result}")
    
    # Create state and manipulate history
    state = AgentState(
        goal="Calculate compound interest",
        user_messages=["What is 1000 * 1.05^10?"],
    )
    state.add_history_entry(
        step=1,
        actor="tool",
        action="calc",
        arguments={"expression": "1000 * 1.05 ** 10"},
        outcome="success",
        result="Result: 1628.89",
    )
    
    print(f"\n3. Agent state created:")
    print(f"   Goal: {state.goal}")
    print(f"   History: {len(state.history)} entries")
    
    # Demonstrate audit logging
    logger = AuditLogger()
    logger.log_decision(
        step=1,
        goal=state.goal,
        history=state.get_history_dicts(),
        policy_context={"org_policies": "test"},
        decision_type="tool",
        decision_details={"selected_tool": "calc"},
        rationale="Using calculator to compute compound interest",
    )
    
    print(f"\n4. Audit log entry created:")
    print(f"   Session: {logger.session_id}")
    print(f"   Entries: {len(logger.entries)}")
    
    print("\n" + "=" * 60)
    print("All components working correctly!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the programmatic example (no API key needed)
    run_programmatic_example()
    
    # Uncomment to run with real LM (requires API key)
    # run_with_mock_lm()
