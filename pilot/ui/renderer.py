"""Rich rendering for the terminal UI."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

# Custom theme
PILOT_THEME = Theme({
    "user": "bold cyan",
    "assistant": "white",
    "tool.name": "bold yellow",
    "tool.success": "bold green",
    "tool.error": "bold red",
    "tool.running": "bold yellow",
    "status": "dim",
    "header": "bold magenta",
})


class Renderer:
    """Handles all Rich rendering for the terminal UI."""

    def __init__(self) -> None:
        self.console = Console(theme=PILOT_THEME)

    def render_header(self, model: str, base_url: str) -> None:
        """Render the application header."""
        header_text = Text()
        header_text.append("  PILOT ", style="bold white on blue")
        header_text.append(" AI Coding Agent\n", style="bold white")
        header_text.append(f"  Model: {model}", style="dim")
        header_text.append(" | ", style="dim")
        header_text.append(base_url, style="dim")

        self.console.print(Panel(
            header_text,
            border_style="blue",
            padding=(0, 1),
        ))

    def render_user_message(self, text: str) -> None:
        """Render a user message."""
        self.console.print()
        self.console.print(Text(" You ", style="bold white on cyan"), end=" ")
        self.console.print(text, style="user")

    def render_assistant_text(self, text: str) -> None:
        """Render assistant response as markdown."""
        self.console.print()
        self.console.print(Text(" Pilot ", style="bold white on blue"), end=" ")
        try:
            md = Markdown(text)
            self.console.print(md)
        except Exception:
            self.console.print(text)

    def render_streaming_start(self) -> None:
        """Signal the start of a streaming response."""
        self.console.print()
        self.console.print(Text(" Pilot ", style="bold white on blue"), end=" ")

    def render_streaming_delta(self, text: str) -> None:
        """Render a single streaming text delta (no newline)."""
        self.console.print(text, end="", highlight=False)

    def render_streaming_end(self) -> None:
        """Signal the end of a streaming response."""
        self.console.print()  # Final newline

    def render_tool_start(self, name: str, arguments: dict) -> None:
        """Render the start of a tool call."""
        self.console.print()

        # Format arguments nicely
        args_lines = []
        for key, value in arguments.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            args_lines.append(f"  {key}: {val_str}")
        args_text = "\n".join(args_lines) if args_lines else "  (no arguments)"

        self.console.print(Panel(
            f"[tool.running]⏳ Running...[/]\n{args_text}",
            title=f"[tool.name]🔧 {name}[/]",
            border_style="yellow",
            padding=(0, 1),
        ))

    def render_tool_result(self, name: str, success: bool, output: str, error: str | None = None) -> None:
        """Render the result of a tool call."""
        if success:
            icon = "✅"
            style = "green"
            content = output
        else:
            icon = "❌"
            style = "red"
            content = error or output

        # Truncate very long output for display
        if len(content) > 2000:
            content = content[:2000] + f"\n... ({len(content)} total chars)"

        self.console.print(Panel(
            f"[tool.{'success' if success else 'error'}]{icon} {'Done' if success else 'Failed'}[/]\n{content}",
            title=f"[tool.name]🔧 {name}[/]",
            border_style=style,
            padding=(0, 1),
        ))

    def render_error(self, error: str) -> None:
        """Render an error message."""
        self.console.print()
        self.console.print(Panel(
            f"[tool.error]{error}[/]",
            title="[tool.error]Error[/]",
            border_style="red",
            padding=(0, 1),
        ))

    def render_status(self, text: str) -> None:
        """Render a status message."""
        self.console.print(f"[status]  {text}[/]")

    def render_divider(self) -> None:
        """Render a horizontal divider."""
        self.console.rule(style="dim")

    def render_help(self) -> None:
        """Render the help message."""
        help_text = """
**Available Commands:**

| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/clear` | Clear conversation history |
| `/config` | Show current configuration |
| `/tools` | List available tools |
| `/quit` | Exit Pilot |

**Tips:**
- Just type naturally — Pilot will figure out which tools to use
- Pilot can read/write files, run commands, fetch web pages, and control apps
- Use Ctrl+C to interrupt a running operation
"""
        self.console.print(Markdown(help_text))

    def render_config(self, config_dict: dict) -> None:
        """Render current configuration."""
        lines = []
        for section, values in config_dict.items():
            lines.append(f"[bold]{section}:[/]")
            if isinstance(values, dict):
                for k, v in values.items():
                    if k == "system_prompt":
                        v = v[:80] + "..." if len(str(v)) > 80 else v
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {values}")
        self.console.print(Panel(
            "\n".join(lines),
            title="[header]Configuration[/]",
            border_style="magenta",
        ))

    def render_tools_list(self, tools: list[str]) -> None:
        """Render available tools list."""
        self.console.print(Panel(
            "\n".join(f"  • {t}" for t in tools),
            title=f"[header]Available Tools ({len(tools)})[/]",
            border_style="magenta",
        ))

    def render_connection_status(self, connected: bool) -> None:
        """Render connection status."""
        if connected:
            self.console.print("[tool.success]  ✅ Connected to LLM API[/]")
        else:
            self.console.print("[tool.error]  ❌ Cannot reach LLM API — is the server running?[/]")

    def render_token_count(self, input_tokens: int, output_tokens: int) -> None:
        """Render token usage."""
        self.console.print(
            f"[status]  Tokens: ↑{input_tokens:,} ↓{output_tokens:,} "
            f"(total: {input_tokens + output_tokens:,})[/]"
        )
