"""Terminal UI — interactive prompt with Rich rendering."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTStyle

from pilot.ui.renderer import Renderer

if TYPE_CHECKING:
    from pilot.agent import Agent


# prompt_toolkit style
PT_STYLE = PTStyle.from_dict({
    "prompt": "ansicyan bold",
})


class Terminal:
    """Interactive terminal UI for the Pilot agent."""

    def __init__(self) -> None:
        self.renderer = Renderer()
        self.session: PromptSession = PromptSession(
            history=InMemoryHistory(),
            style=PT_STYLE,
        )
        self._agent: Agent | None = None

    def set_agent(self, agent: Agent) -> None:
        self._agent = agent

    def show_header(self, model: str, base_url: str) -> None:
        self.renderer.render_header(model, base_url)

    def show_connection_status(self, connected: bool) -> None:
        self.renderer.render_connection_status(connected)

    def show_help(self) -> None:
        self.renderer.render_help()

    def show_config(self, config_dict: dict) -> None:
        self.renderer.render_config(config_dict)

    def show_tools(self, tool_names: list[str]) -> None:
        self.renderer.render_tools_list(tool_names)

    def show_error(self, error: str) -> None:
        self.renderer.render_error(error)

    def show_status(self, text: str) -> None:
        self.renderer.render_status(text)

    def show_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.renderer.render_token_count(input_tokens, output_tokens)

    async def get_input(self) -> str | None:
        """Get user input from the prompt. Returns None on EOF/Ctrl+D."""
        try:
            # Run prompt_toolkit in a thread since it's blocking
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.prompt(
                    HTML("<prompt>pilot&gt; </prompt>"),
                ),
            )
            return result.strip() if result else None
        except (EOFError, KeyboardInterrupt):
            return None

    def handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns True if command was handled."""
        cmd = command.lower().strip()

        if cmd == "/help":
            self.show_help()
            return True

        elif cmd == "/clear":
            if self._agent:
                self._agent.clear_history()
            self.renderer.console.clear()
            self.renderer.render_status("Conversation cleared.")
            return True

        elif cmd == "/config":
            if self._agent:
                cfg = self._agent.config
                self.show_config({
                    "API": {
                        "base_url": cfg.api.base_url,
                        "model": cfg.api.model,
                        "api_key": cfg.api.api_key[:8] + "..." if len(cfg.api.api_key) > 8 else cfg.api.api_key,
                    },
                    "Agent": {
                        "max_iterations": cfg.agent.max_iterations,
                        "temperature": cfg.agent.temperature,
                        "system_prompt": cfg.agent.system_prompt,
                    },
                })
            return True

        elif cmd == "/tools":
            if self._agent:
                self.show_tools(self._agent.registry.tool_names)
            return True

        elif cmd in ("/quit", "/exit", "/q"):
            self.renderer.render_status("Goodbye!")
            raise SystemExit(0)

        return False

    async def run(self, agent: Agent) -> None:
        """Main loop — get input, process, display."""
        self.set_agent(agent)

        # Header
        self.show_header(agent.config.api.model, agent.config.api.base_url)

        # Test connection
        self.show_status("Connecting to LLM API...")
        connected = await agent.llm.test_connection()
        self.show_connection_status(connected)

        if not connected:
            self.show_status(
                f"Make sure your LLM server is running at {agent.config.api.base_url}"
            )

        self.show_status(f"Loaded {len(agent.registry)} tools: {', '.join(agent.registry.tool_names)}")
        self.show_status("Type /help for commands, or just start chatting.\n")

        while True:
            try:
                user_input = await self.get_input()

                if user_input is None:
                    continue

                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    if self.handle_slash_command(user_input):
                        continue

                # Show user message
                self.renderer.render_user_message(user_input)

                # Process with agent
                await agent.process_message(user_input, self)

                # Show token usage
                self.show_tokens(
                    agent.llm.total_input_tokens,
                    agent.llm.total_output_tokens,
                )

            except KeyboardInterrupt:
                self.renderer.console.print("\n[status]  Interrupted. Type /quit to exit.[/]")
                continue
            except SystemExit:
                raise
            except Exception as e:
                self.show_error(f"Unexpected error: {e}")
