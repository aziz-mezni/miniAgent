"""Tool registry — registration, schema export, and dispatch."""

from __future__ import annotations

import json
import logging
from typing import Any

from pilot.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_schemas(self) -> list[dict]:
        """Export all tool schemas in OpenAI format."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any] | str) -> ToolResult:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {name}")

        # Parse arguments if they come as a JSON string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return ToolResult(
                    success=False, output="",
                    error=f"Invalid JSON arguments: {arguments}"
                )

        try:
            return await tool.execute(**arguments)
        except Exception as e:
            logger.exception(f"Tool {name} failed")
            return ToolResult(success=False, output="", error=str(e))

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)


def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools registered."""
    from pilot.tools.file_ops import (
        ReadFileTool, WriteFileTool, EditFileTool, GlobFilesTool, GrepTool
    )
    from pilot.tools.shell import RunCommandTool
    from pilot.tools.web import FetchURLTool, ScrapePageTool
    from pilot.tools.app_control import (
        OpenAppTool, ScreenshotTool, ClickTool, TypeTextTool, HotkeyTool
    )

    registry = ToolRegistry()

    # File operations
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(GlobFilesTool())
    registry.register(GrepTool())

    # Shell
    registry.register(RunCommandTool())

    # Web
    registry.register(FetchURLTool())
    registry.register(ScrapePageTool())

    # App control
    registry.register(OpenAppTool())
    registry.register(ScreenshotTool())
    registry.register(ClickTool())
    registry.register(TypeTextTool())
    registry.register(HotkeyTool())

    return registry
