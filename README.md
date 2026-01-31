# DSPy Agentic Loop

A deterministic, auditable agentic loop built using DSPy as a reasoning compiler.

## Features

- **Multi-step tool invocation** - Execute tools based on LLM decisions
- **Human-in-the-Loop (HITL)** - First-class support for human escalation
- **Streaming support** - Token streaming for rationale and responses
- **Observability** - Full audit trail for replay and compliance

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## Configuration

Set your LLM API key:

```bash
export OPENAI_API_KEY="your-key"
# or
export ANTHROPIC_API_KEY="your-key"
```

## Usage

```python
from agent_loop import Orchestrator, AgentState, PolicyContext

# Create state and context
state = AgentState(goal="Research quantum computing", user_messages=["Tell me about qubits"])
policy_ctx = PolicyContext(org_policies="Be helpful and accurate")

# Run the agent
orchestrator = Orchestrator()
result = orchestrator.run(state, policy_ctx)
print(result.final_response)
```

## Architecture

```
State Snapshot
     ↓
DSPy Policy (decide)
     ↓
{ tool | hitl | final }
     ↓
State Mutation
     ↓
Repeat until final
```

This is a decision system, not a conversational agent.
