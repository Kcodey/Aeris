"""Load skill tool for agent."""

from typing import Dict

from aeris.skills.registry import get_skill_registry
from aeris.tools.base import Tool, ToolParameter, ToolResult


class LoadSkillTool(Tool):
    """Load a skill by name to access its full instructions and workflows."""

    name = "load_skill"
    description = (
        "Load the full body of a named skill into the current context. "
        "Use this when a task needs specialized instructions before you act. "
        "The skill body will be returned as plain text for reference."
    )
    parameters = [
        ToolParameter(
            name="name",
            type="string",
            description="技能名称，如 'Data Analysis'",
            required=True,
        ),
    ]

    async def execute(
        self,
        name: str,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            registry = get_skill_registry()
            text = registry.load_full_text(name)
            return ToolResult(success=True, data={"text": text})
        except RuntimeError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


def register_load_skill_tool(registry):
    """Register load_skill tool."""
    registry.register(LoadSkillTool())
