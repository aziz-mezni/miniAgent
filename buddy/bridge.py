"""Bridge between the Pilot agent and the Buddy GUI.

BuddyBridge duck-types pilot.ui.terminal.Terminal so that
agent.py can call terminal.renderer.render_*() and terminal.show_error()
without any changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buddy.character import CharacterWidget
    from buddy.chat_bubble import ChatBubble
    from buddy.chat_panel import ChatPanel


class BuddyRenderer:
    """Duck-types pilot.ui.renderer.Renderer.

    Every method here maps 1:1 to what agent.py calls on terminal.renderer.
    Instead of printing to a terminal, we update the GUI widgets.
    """

    def __init__(
        self,
        character: CharacterWidget,
        bubble: ChatBubble,
        panel: ChatPanel,
    ) -> None:
        self._char = character
        self._bubble = bubble
        self._panel = panel
        self._streaming_text = ""

    # ── Streaming ─────────────────────────────────────────────────────

    def render_streaming_start(self) -> None:
        self._streaming_text = ""
        self._char.set_state("talk")
        self._panel.start_streaming()

    def render_streaming_delta(self, text: str) -> None:
        self._streaming_text += text
        self._panel.append_streaming(text)
        # Show last portion in speech bubble
        tail = self._streaming_text[-200:]
        self._bubble.show_message(tail, duration=0)  # Don't auto-hide during stream

    def render_streaming_end(self) -> None:
        self._char.set_state("idle")
        self._panel.end_streaming()
        # Show summary in bubble
        summary = self._streaming_text[:300]
        if len(self._streaming_text) > 300:
            summary += "..."
        self._bubble.show_message(summary, duration=8000)

    # ── Tool calls ────────────────────────────────────────────────────

    def render_tool_start(self, name: str, args: dict) -> None:
        self._char.set_state("think")
        self._panel.add_tool_message(name, None, "Running...")
        self._bubble.show_message(f"🔧 Running {name}...", duration=0)

    def render_tool_result(
        self, name: str, success: bool, output: str, error: str | None = None
    ) -> None:
        if success:
            self._char.set_state("idle")
            summary = output[:150] if output else "Done"
        else:
            self._char.set_state("error")
            summary = (error or output)[:150]

        self._panel.add_tool_message(name, success, summary)
        icon = "✅" if success else "❌"
        self._bubble.show_message(f"{icon} {name}: {summary}", duration=4000)

    # ── These are called by Renderer but not by agent.py directly ────
    # We provide them for completeness / future use.

    def render_error(self, error: str) -> None:
        self._char.set_state("error")
        self._panel.add_error_message(error)
        self._bubble.show_message(f"❌ {error[:200]}", duration=6000)

    def render_status(self, text: str) -> None:
        self._bubble.show_message(text, duration=3000)


class BuddyBridge:
    """Duck-types pilot.ui.terminal.Terminal for agent.py compatibility.

    agent.py calls:
        terminal.renderer.render_streaming_start()
        terminal.renderer.render_streaming_delta(text)
        terminal.renderer.render_streaming_end()
        terminal.renderer.render_tool_start(name, args)
        terminal.renderer.render_tool_result(name, success, output, error)
        terminal.show_error(error)
    """

    def __init__(self, renderer: BuddyRenderer) -> None:
        self.renderer = renderer

    def show_error(self, error: str) -> None:
        self.renderer.render_error(error)
