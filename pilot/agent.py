"""Core agent loop — message → LLM → tools → loop."""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

from pilot.config import Config
from pilot.llm import LLMClient, StreamDelta
from pilot.tool_registry import ToolRegistry, create_default_registry

if TYPE_CHECKING:
    from pilot.ui.terminal import Terminal

logger = logging.getLogger(__name__)


class Agent:
    """Core agent that orchestrates the LLM-tool execution cycle."""

    def __init__(self, config: Config, registry: ToolRegistry | None = None) -> None:
        self.config = config
        self.llm = LLMClient(config)
        self.registry = registry or create_default_registry()
        self.history: list[dict[str, Any]] = []

    def clear_history(self) -> None:
        self.history.clear()

    def _build_messages(self, user_message: str) -> list[dict[str, Any]]:
        """Build the full message array for the LLM."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.config.agent.system_prompt},
        ]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def process_message(self, user_message: str, terminal: Terminal) -> None:
        """Process a user message through the agent loop."""
        # Add user message to history
        self.history.append({"role": "user", "content": user_message})

        tools_schema = self.registry.get_all_schemas()
        iteration = 0

        while iteration < self.config.agent.max_iterations:
            iteration += 1

            # Build messages for LLM
            messages = [
                {"role": "system", "content": self.config.agent.system_prompt},
            ] + self.history

            # Stream the response
            response_content = ""
            tool_calls_acc: dict[int, dict] = {}
            streaming_started = False

            try:
                async for delta in self.llm.chat_stream(messages, tools_schema):
                    # Handle text content streaming
                    if delta.content:
                        if not streaming_started:
                            terminal.renderer.render_streaming_start()
                            streaming_started = True
                        terminal.renderer.render_streaming_delta(delta.content)
                        response_content += delta.content

                    # Handle tool call streaming
                    if delta.tool_call_index is not None:
                        idx = delta.tool_call_index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}

                        if delta.tool_call_id:
                            tool_calls_acc[idx]["id"] = delta.tool_call_id
                        if delta.tool_call_name:
                            tool_calls_acc[idx]["name"] = delta.tool_call_name
                        if delta.tool_call_arguments:
                            tool_calls_acc[idx]["arguments"] += delta.tool_call_arguments

            except Exception as e:
                if streaming_started:
                    terminal.renderer.render_streaming_end()
                terminal.show_error(f"LLM error: {e}")
                return

            if streaming_started:
                terminal.renderer.render_streaming_end()

            # If we got tool calls, execute them
            if tool_calls_acc:
                # Build assistant message with tool calls for history
                assistant_msg: dict[str, Any] = {"role": "assistant"}
                if response_content:
                    assistant_msg["content"] = response_content
                else:
                    assistant_msg["content"] = None

                openai_tool_calls = []
                for idx in sorted(tool_calls_acc.keys()):
                    tc = tool_calls_acc[idx]
                    openai_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    })
                assistant_msg["tool_calls"] = openai_tool_calls
                self.history.append(assistant_msg)

                # Execute each tool call
                for tc_data in openai_tool_calls:
                    tool_name = tc_data["function"]["name"]
                    tool_args_str = tc_data["function"]["arguments"]
                    tool_call_id = tc_data["id"]

                    # Parse arguments
                    try:
                        tool_args = json.loads(tool_args_str) if tool_args_str else {}
                    except json.JSONDecodeError:
                        tool_args = {}

                    # Show tool start
                    terminal.renderer.render_tool_start(tool_name, tool_args)

                    # Execute tool
                    result = await self.registry.execute(tool_name, tool_args)

                    # Show tool result
                    terminal.renderer.render_tool_result(
                        tool_name, result.success, result.output, result.error
                    )

                    # Add tool result to history
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result.to_message(),
                    })

                # Continue the loop — LLM might want to call more tools
                continue

            else:
                # Text-only response — we're done
                if response_content:
                    self.history.append({"role": "assistant", "content": response_content})
                return

        # Hit iteration limit
        terminal.show_error(
            f"Reached maximum iterations ({self.config.agent.max_iterations}). "
            "Stopping to prevent infinite loops."
        )
