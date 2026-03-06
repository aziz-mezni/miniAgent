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
        # Think-tag filter state
        self._think_buffer = ""
        self._inside_think = False

    # ── Think-tag filtering ────────────────────────────────────────────

    def _filter_think_tags(self, text: str) -> str:
        """Filter out <think>...</think> content from streaming text.

        Handles tags that span multiple streaming chunks by buffering
        partial tag fragments at chunk boundaries.
        """
        result: list[str] = []
        self._think_buffer += text

        while self._think_buffer:
            if self._inside_think:
                # Look for closing </think>
                end_idx = self._think_buffer.find("</think>")
                if end_idx != -1:
                    # Skip everything up to and including </think>
                    self._think_buffer = self._think_buffer[end_idx + 8:]
                    self._inside_think = False
                    # Strip leading whitespace/newline after </think>
                    self._think_buffer = self._think_buffer.lstrip("\n\r")
                else:
                    # Still inside think block — keep last 8 chars
                    # in case "</think>" is split across chunks
                    if len(self._think_buffer) > 8:
                        self._think_buffer = self._think_buffer[-8:]
                    break
            else:
                # Look for opening <think>
                start_idx = self._think_buffer.find("<think>")
                if start_idx != -1:
                    # Emit everything before the tag
                    before = self._think_buffer[:start_idx]
                    if before:
                        result.append(before)
                    self._think_buffer = self._think_buffer[start_idx + 7:]
                    self._inside_think = True
                else:
                    # Check if buffer ends with a prefix of "<think>"
                    tag = "<think>"
                    safe_end = len(self._think_buffer)
                    for i in range(1, len(tag)):
                        if self._think_buffer.endswith(tag[:i]):
                            safe_end = len(self._think_buffer) - i
                            break
                    if safe_end > 0:
                        result.append(self._think_buffer[:safe_end])
                    self._think_buffer = self._think_buffer[safe_end:]
                    break

        return "".join(result)

    # ── Streaming ─────────────────────────────────────────────────────

    def render_streaming_start(self) -> None:
        self._streaming_text = ""
        self._think_buffer = ""
        self._inside_think = False
        self._char.set_state("talk")
        self._panel.start_streaming()

    def render_streaming_delta(self, text: str) -> None:
        filtered = self._filter_think_tags(text)
        if not filtered:
            return  # Content was inside <think> block

        self._streaming_text += filtered
        self._panel.append_streaming(filtered)
        # Show last portion in speech bubble
        tail = self._streaming_text[-200:]
        self._bubble.show_message(tail, duration=0)  # Don't auto-hide during stream

    def render_streaming_end(self) -> None:
        # Flush any remaining buffer (if stream ends outside a think block)
        if self._think_buffer and not self._inside_think:
            self._streaming_text += self._think_buffer
            self._panel.append_streaming(self._think_buffer)
        self._think_buffer = ""
        self._inside_think = False

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
