from .tool_manager import ToolManager, Tool

def tool(name: str, description: str, parameters: dict):
    """
    Decorator to register a tool in the global registry.
    
    Example:
        @tool(
            name="get_weather",
            description="Get current weather for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        )
        def get_weather(location: str):
            return f"Weather in {location}: sunny"
    """
    def wrapper(func):
        ToolManager().register(
            Tool(
                name=name,
                description=description,
                parameters=parameters,
                func=func
            )
        )
        return func
    return wrapper
