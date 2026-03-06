"""Main floating window — frameless, transparent, draggable."""

from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QWidget, QMenu, QApplication

from buddy.character import CharacterWidget
from buddy.chat_bubble import ChatBubble
from buddy.chat_panel import ChatPanel
from buddy.bridge import BuddyBridge, BuddyRenderer


class BuddyWindow(QWidget):
    """Frameless transparent floating window with character + chat."""

    def __init__(self) -> None:
        super().__init__()

        # ── Window flags ──
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # ── State ──
        self._drag_pos: QPointF | None = None
        self._pinned = True
        self._pending_region: tuple[int, int, int, int] | None = None

        # ── Character widget ──
        config_path = str(Path(__file__).parent / "character_config.json")
        self.character = CharacterWidget(config_path, parent=self)

        # Set window size to match character
        self.setFixedSize(self.character.size())

        # ── Chat bubble (separate top-level window) ──
        self.bubble = ChatBubble()

        # ── Chat panel (separate top-level window) ──
        self.panel = ChatPanel()
        self.panel.message_submitted.connect(self._on_user_message)
        self.panel.new_session_requested.connect(self._on_new_session)
        self.panel.vision_requested.connect(self._on_vision_request)
        self.panel.settings_requested.connect(self._open_settings)

        # ── Character click → toggle panel ──
        self.character.clicked.connect(self._toggle_panel)

        # ── Agent (set later by app.py) ──
        self.agent: Any = None
        self.bridge: BuddyBridge | None = None
        self._processing = False

        # ── Overlay (lazy) ──
        self._overlay = None

        # Position at bottom-right of screen
        self._position_default()

    def _position_default(self) -> None:
        """Place at bottom-right corner of primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 50
            y = geo.bottom() - self.height() - 50
            self.move(x, y)

    def _update_satellite_positions(self) -> None:
        """Update bubble and panel positions relative to character."""
        global_pos = self.mapToGlobal(self.character.pos())

        self.bubble.position_above(
            QPointF(global_pos.x(), global_pos.y()),
            self.character.width(),
        )

        self.panel.position_beside(
            global_pos.x(),
            global_pos.y(),
            self.character.height(),
        )

    def _toggle_panel(self) -> None:
        """Toggle the chat panel visibility."""
        self._update_satellite_positions()
        self.panel.toggle()

    # ── Message handling ──────────────────────────────────────────────

    def _on_user_message(self, text: str) -> None:
        """Handle a message from the chat panel input."""
        if self._processing:
            return

        if not self.agent or not self.bridge:
            self.bubble.show_message("Agent not connected!", duration=3000)
            return

        # Handle slash commands
        if text.startswith("/"):
            self._handle_slash(text)
            return

        # Add user message to panel
        self.panel.add_user_message(text)

        # Process async
        self._processing = True
        asyncio.ensure_future(self._process(text))

    async def _process(self, text: str) -> None:
        """Process message through the agent."""
        try:
            await self.agent.process_message(text, self.bridge)
        except Exception as e:
            self.bridge.show_error(f"Error: {e}")
        finally:
            self._processing = False
            # Update token counter
            if self.agent:
                self.panel.update_token_count(
                    self.agent.llm.total_input_tokens,
                    self.agent.llm.total_output_tokens,
                )

    # ── New session ───────────────────────────────────────────────────

    def _on_new_session(self) -> None:
        """Clear conversation history and chat messages."""
        if self.agent:
            self.agent.clear_history()
        self.panel.clear()
        self.bubble.show_message("New session started!", duration=2000)

    # ── Slash commands ────────────────────────────────────────────────

    def _handle_slash(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.lower().strip()

        if cmd == "/clear":
            self._on_new_session()

        elif cmd == "/help":
            help_text = (
                "Commands:\n"
                "/clear — Clear chat\n"
                "/tools — List tools\n"
                "/hide — Hide panel\n"
                "/quit — Exit"
            )
            self.panel.add_assistant_message(help_text)

        elif cmd == "/tools":
            if self.agent:
                tools = ", ".join(self.agent.registry.tool_names)
                self.panel.add_assistant_message(f"Tools: {tools}")

        elif cmd == "/hide":
            self.panel.toggle()

        elif cmd in ("/quit", "/exit"):
            QApplication.quit()

    # ── Vision ────────────────────────────────────────────────────────

    def _on_vision_request(self, mode: str) -> None:
        """Handle vision request from chat panel."""
        if self._processing:
            self.bubble.show_message("Wait for current task...", duration=2000)
            return

        if mode == "full":
            self._capture_full_screen()
        elif mode == "section":
            self._start_section_selection()

    def _capture_full_screen(self) -> None:
        """Hide windows, capture full screen after delay."""
        self.hide()
        self.bubble.hide()
        self.panel.hide()
        QTimer.singleShot(300, self._do_full_capture)

    def _do_full_capture(self) -> None:
        """Actually capture the full screen."""
        try:
            import pyautogui

            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            self.show()
            self._update_satellite_positions()
            self._send_vision_message(b64, f"Screenshot ({img.width}×{img.height})")
        except Exception as e:
            self.show()
            self.bubble.show_message(f"Screenshot failed: {e}", duration=4000)

    def _start_section_selection(self) -> None:
        """Show the selection overlay."""
        self.hide()
        self.bubble.hide()
        self.panel.hide()
        QTimer.singleShot(300, self._show_overlay)

    def _show_overlay(self) -> None:
        """Create and show the overlay after windows are hidden."""
        from buddy.screenshot_overlay import ScreenshotOverlay

        self._overlay = ScreenshotOverlay()
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.selection_cancelled.connect(self._on_selection_cancelled)
        self._overlay.start_selection()

    def _on_region_selected(self, rect) -> None:
        """Capture the selected region."""
        if self._overlay:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

        self._pending_region = (rect.x(), rect.y(), rect.width(), rect.height())
        QTimer.singleShot(150, self._do_region_capture)

    def _do_region_capture(self) -> None:
        """Capture the region after overlay is fully hidden."""
        try:
            import pyautogui

            region = self._pending_region
            img = pyautogui.screenshot(region=region)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            self.show()
            self._update_satellite_positions()
            self._send_vision_message(b64, f"Region ({region[2]}×{region[3]})")
        except Exception as e:
            self.show()
            self.bubble.show_message(f"Capture failed: {e}", duration=4000)

    def _on_selection_cancelled(self) -> None:
        """User cancelled region selection."""
        if self._overlay:
            self._overlay.deleteLater()
            self._overlay = None
        self.show()
        self._update_satellite_positions()

    def _send_vision_message(self, b64_image: str, description: str) -> None:
        """Send a vision message to the agent."""
        if not self.agent or not self.bridge:
            self.bubble.show_message("Agent not connected!", duration=3000)
            return

        self.panel.add_user_message(f"📷 {description}")
        self._processing = True
        asyncio.ensure_future(self._process_vision(b64_image))

    async def _process_vision(self, b64_image: str) -> None:
        """Process a vision message — bypasses agent.process_message
        because we need multimodal content (list vs string)."""
        try:
            # Build multimodal user message
            vision_content = [
                {
                    "type": "text",
                    "text": "Analyze this screenshot. Describe what you see and any notable details.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                },
            ]

            # Add to agent history
            self.agent.history.append({"role": "user", "content": vision_content})

            # Build messages
            messages = [
                {"role": "system", "content": self.agent.config.agent.system_prompt},
            ] + self.agent.history

            # Stream the response
            response_content = ""
            streaming_started = False

            async for delta in self.agent.llm.chat_stream(messages):
                if delta.content:
                    if not streaming_started:
                        self.bridge.renderer.render_streaming_start()
                        streaming_started = True
                    self.bridge.renderer.render_streaming_delta(delta.content)
                    response_content += delta.content

            if streaming_started:
                self.bridge.renderer.render_streaming_end()

            if response_content:
                self.agent.history.append(
                    {"role": "assistant", "content": response_content}
                )

        except Exception as e:
            self.bridge.show_error(f"Vision error: {e}")
        finally:
            self._processing = False
            if self.agent:
                self.panel.update_token_count(
                    self.agent.llm.total_input_tokens,
                    self.agent.llm.total_output_tokens,
                )

    # ── Settings ──────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Open the settings dialog."""
        if not self.agent:
            return

        from buddy.settings_panel import SettingsDialog

        dialog = SettingsDialog(self.agent.config)
        dialog.exec()

        # Refresh LLM client if base_url or api_key changed
        if dialog.needs_client_refresh:
            self._refresh_llm_client()

    def _refresh_llm_client(self) -> None:
        """Recreate the AsyncOpenAI client with updated config."""
        if not self.agent:
            return

        from openai import AsyncOpenAI

        self.agent.llm.client = AsyncOpenAI(
            base_url=self.agent.config.api.base_url,
            api_key=self.agent.config.api.api_key,
        )

        asyncio.ensure_future(self._test_new_connection())

    async def _test_new_connection(self) -> None:
        """Test connection after settings change."""
        try:
            connected = await self.agent.llm.test_connection()
            if connected:
                model = self.agent.config.api.model
                self.bubble.show_message(f"✅ Connected to {model}!", duration=4000)
                self.character.set_state("wave")
                await asyncio.sleep(1.5)
                self.character.set_state("idle")
            else:
                url = self.agent.config.api.base_url
                self.bubble.show_message(
                    f"❌ Cannot reach {url}", duration=6000
                )
                self.character.set_state("error")
        except Exception as e:
            self.bubble.show_message(f"❌ Connection error: {e}", duration=6000)

    # ── Dragging ──────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None:
            delta = event.globalPosition() - self._drag_pos
            new_pos = self.pos() + delta.toPoint()
            self.move(new_pos)
            self._drag_pos = event.globalPosition()
            self._update_satellite_positions()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ── Context menu (right-click) ────────────────────────────────────

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                color: #1A1A1A;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
        """)

        toggle_chat = menu.addAction("💬 Toggle Chat")
        toggle_chat.triggered.connect(self._toggle_panel)

        clear_action = menu.addAction("🗑️ Clear History")
        clear_action.triggered.connect(self._on_new_session)

        menu.addSeparator()

        # Pin / Unpin
        pin_text = "📌 Unpin from Top" if self._pinned else "📌 Pin on Top"
        pin_action = menu.addAction(pin_text)
        pin_action.triggered.connect(self._toggle_pin)

        settings_action = menu.addAction("⚙ Settings")
        settings_action.triggered.connect(self._open_settings)

        menu.addSeparator()

        quit_action = menu.addAction("❌ Quit")
        quit_action.triggered.connect(QApplication.quit)

        menu.exec(event.globalPos())

    def _toggle_pin(self) -> None:
        """Toggle always-on-top."""
        self._pinned = not self._pinned
        flags = self.windowFlags()
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # ── Show override — position satellites ───────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_satellite_positions()
        self.bubble.show_message("👋 Hi! Click me to chat.", duration=5000)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if self.isVisible():
            self._update_satellite_positions()
