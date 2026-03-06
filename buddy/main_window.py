"""Main floating window — frameless, transparent, draggable."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QPointF
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

        # ── Drag state ──
        self._drag_pos: QPointF | None = None

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

        # ── Character click → toggle panel ──
        self.character.clicked.connect(self._toggle_panel)

        # ── Agent (set later by app.py) ──
        self.agent: Any = None
        self.bridge: BuddyBridge | None = None
        self._processing = False

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

    def _handle_slash(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.lower().strip()

        if cmd == "/clear":
            if self.agent:
                self.agent.clear_history()
            self.panel.clear()
            self.bubble.show_message("Chat cleared!", duration=2000)

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
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
        """)

        toggle_chat = menu.addAction("💬 Toggle Chat")
        toggle_chat.triggered.connect(self._toggle_panel)

        clear_action = menu.addAction("🗑️ Clear History")
        clear_action.triggered.connect(lambda: self._handle_slash("/clear"))

        menu.addSeparator()

        quit_action = menu.addAction("❌ Quit")
        quit_action.triggered.connect(QApplication.quit)

        menu.exec(event.globalPos())

    # ── Show override — position satellites ───────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_satellite_positions()
        self.bubble.show_message("👋 Hi! Click me to chat.", duration=5000)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if self.isVisible():
            self._update_satellite_positions()
