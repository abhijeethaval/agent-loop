"""DSPy signature for agent policy decisions.

This defines the Act signature that encodes policy precedence rules.
"""

import dspy


class Act(dspy.Signature):
    """Decide the next action for the agent.
    
    CRITICAL: ALWAYS CHECK HISTORY FIRST!
    - The history contains previous actions and human responses
    - If you already asked questions via HITL and got responses, USE THAT INFORMATION
    - DO NOT ask the same or similar questions again
    - After receiving human feedback, proceed to use tools or provide final response
    
    DECISION TYPE RULES:
    
    Use 'hitl' (Human-in-the-Loop) ONLY when:
    - You need information from the user that is NOT already in history
    - This is your FIRST time asking (check history for previous hitl_request/hitl_response)
    - Never use HITL more than once unless the user's response was unclear
    
    Use 'tool' when:
    - You have gathered user information from history (via previous HITL)
    - You can now execute a tool to help achieve the goal
    - IMPORTANT: Always include ALL required parameters in arguments JSON!
    - Look at the tool description for the expected JSON format
    - If a previous tool returned data (like URLs from search_web), extract and use those values
    
    Use 'final' when:
    - You have enough information from search results or tools to answer the user
    - The search results contain sufficient information to synthesize an answer
    - DO NOT keep searching if you already have relevant results - use them!
    - The goal is achieved or cannot be achieved
    
    Policy precedence (in order):
    1. Organization policies override all other inputs
    2. Industry rules override domain guidelines
    3. Domain guidelines inform approach
    4. User goal drives the action
    """
    
    # Input fields - State
    goal: str = dspy.InputField(desc="The goal the agent is trying to achieve")
    user_messages: list[str] = dspy.InputField(desc="Messages from the user")
    history: list[dict] = dspy.InputField(
        desc="IMPORTANT: Contains previous actions including hitl_request (questions asked) and hitl_response (user answers). Check this before asking new questions!"
    )
    
    # Input fields - Policy Context
    org_policies: str = dspy.InputField(
        desc="Organization-level policies (highest priority)"
    )
    industry_rules: str = dspy.InputField(
        desc="Industry or regulatory rules"
    )
    domain_guidelines: str = dspy.InputField(
        desc="Domain-specific guidelines"
    )
    
    # Input fields - Available tools
    available_tools: str = dspy.InputField(
        desc="Description of available tools and their parameters"
    )
    
    # Output fields
    rationale: str = dspy.OutputField(
        desc="First, state what information you found in history. Then explain your decision."
    )
    decision_type: str = dspy.OutputField(
        desc="MUST be exactly one of: 'tool', 'hitl', 'final'. If history contains hitl_response, you likely should NOT use 'hitl' again."
    )
    selected_tool: str = dspy.OutputField(
        desc="Name of tool to execute. Required if decision_type is 'tool', otherwise empty string."
    )
    arguments: str = dspy.OutputField(
        desc='JSON string with ALL required arguments. Example: {\"url\": \"https://...\"}. CRITICAL: Extract actual values (like URLs) from previous tool results in history. Never leave required fields empty.'
    )
    hitl_request: str = dspy.OutputField(
        desc="Questions for the user. Only use if history does NOT already contain user responses to similar questions."
    )
    final_response: str = dspy.OutputField(
        desc="Complete final response to the user. Required if decision_type is 'final', otherwise empty string."
    )
    action_confirmation: str = dspy.OutputField(
        desc="Confirmation of the action taken and its result. Use this to summarize what was done when decision_type is 'tool' or 'final'. Empty string if not applicable."
    )

