from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, Callable


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None


class Tool(ABC):
    """Base class for tools."""

    name: str
    description: str
    parameters: List[ToolParameter]

    def __init__(self):
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    """Registry for tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
        self._schemas[tool.name] = tool.to_openai_schema()

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: List[ToolParameter],
    ):
        """Register a function as a tool."""
        # Create a wrapper Tool class
        class FunctionTool(Tool):
            def __init__(self):
                self.name = name
                self.description = description
                self.parameters = parameters
                self._func = func

            async def execute(self, **kwargs) -> ToolResult:
                try:
                    result = await self._func(**kwargs)
                    return ToolResult(success=True, data=result)
                except Exception as e:
                    return ToolResult(success=False, data=None, error=str(e))

        self.register(FunctionTool())

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM."""
        return list(self._schemas.values())

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{name}' not found",
            )
        return await tool.execute(**arguments)


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry