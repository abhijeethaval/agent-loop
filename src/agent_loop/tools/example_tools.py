"""Example tools for demonstration.

These are sample tools to demonstrate the agent loop.
"""

import random

from agent_loop.models.tool_result import ToolResult


def search_web(query: str) -> ToolResult:
    """Simulate a web search.
    
    Args:
        query: Search query string
        
    Returns:
        ToolResult with simulated search results
    """
    # Simulated search results
    results = [
        f"Result 1: Information about '{query}' from Wikipedia",
        f"Result 2: '{query}' - Latest news and updates",
        f"Result 3: Understanding '{query}' - A comprehensive guide",
    ]
    return ToolResult.success(
        message=f"Found {len(results)} results for '{query}'",
        data={"results": results, "query": query}
    )


def calculate(expression: str) -> ToolResult:
    """Evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        ToolResult with the calculated result
    """
    try:
        # Use eval with restricted builtins for safety
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow, "int": int, "float": float,
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return ToolResult.success(
            message=f"Result: {result}",
            data={"expression": expression, "result": result}
        )
    except Exception as e:
        return ToolResult.error(f"Failed to evaluate '{expression}': {e}")


def get_weather(location: str) -> ToolResult:
    """Get simulated weather for a location.
    
    Args:
        location: City or location name
        
    Returns:
        ToolResult with simulated weather data
    """
    # Simulated weather data
    conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear"]
    temp = random.randint(15, 35)
    humidity = random.randint(30, 80)
    condition = random.choice(conditions)
    
    return ToolResult.success(
        message=f"Weather in {location}: {condition}, {temp}°C, {humidity}% humidity",
        data={
            "location": location,
            "temperature": temp,
            "humidity": humidity,
            "condition": condition,
        }
    )


def get_current_time(timezone: str = "UTC") -> ToolResult:
    """Get the current time.
    
    Args:
        timezone: Timezone name (simulated)
        
    Returns:
        ToolResult with current time
    """
    from datetime import datetime
    
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    return ToolResult.success(
        message=f"Current time ({timezone}): {time_str}",
        data={"time": time_str, "timezone": timezone}
    )


def create_default_registry():
    """Create a registry with default example tools.
    
    Returns:
        ToolRegistry with example tools registered
    """
    from agent_loop.tools.registry import ToolRegistry
    
    registry = ToolRegistry()
    
    registry.register(
        "search_web",
        search_web,
        "Search the web for information. Args: query (str)"
    )
    registry.register(
        "calculate",
        calculate,
        "Evaluate a mathematical expression. Args: expression (str)"
    )
    registry.register(
        "get_weather",
        get_weather,
        "Get weather for a location. Args: location (str)"
    )
    registry.register(
        "get_current_time",
        get_current_time,
        "Get current time. Args: timezone (str, optional)"
    )
    
    return registry
