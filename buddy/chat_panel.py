"""Mini chat panel — expandable chat with input field and message history."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy, QMenu,
)


class MessageBubble(QFrame):
    """A single message bubble in the chat panel."""

    def __init__(
        self,
        text: str,
        role: str = "assistant",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._role = role

        # Style based on role
        if role == "user":
            bg = "#DCF8C6"
        elif role == "tool":
            bg = "#FFF3E0"
        elif role == "error":
            bg = "#FFCDD2"
        else:  # assistant
            bg = "#FFFFFF"

        # Determine text color per role
        if role == "error":
            text_color = "#B71C1C"
        elif role == "tool":
            text_color = "#4E342E"
        else:
            text_color = "#1A1A1A"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: 10px;
                padding: 8px 12px;
                margin: 2px 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setFont(QFont("Segoe UI", 9))
        self._label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {text_color};
                padding: 2px 4px;
                margin: 0;
            }}
        """)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setMinimumWidth(40)
        layout.addWidget(self._label)

        # Copy button (assistant messages only)
        if role == "assistant":
            self._copy_btn = QPushButton("📋")
            self._copy_btn.setFixedSize(22, 22)
            self._copy_btn.setToolTip("Copy")
            self._copy_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 11px;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.08);
                    border-radius: 11px;
                }
            """)
            self._copy_btn.clicked.connect(self._copy_text)
            self._copy_btn.hide()
            layout.addWidget(self._copy_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _copy_text(self) -> None:
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._label.text())
        self._copy_btn.setText("✓")
        QTimer.singleShot(1500, lambda: self._copy_btn.setText("📋"))

    def enterEvent(self, event) -> None:
        if hasattr(self, "_copy_btn"):
            self._copy_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if hasattr(self, "_copy_btn"):
            self._copy_btn.hide()
        super().leaveEvent(event)

    def append_text(self, text: str) -> None:
        self._label.setText(self._label.text() + text)

    def set_text(self, text: str) -> None:
        self._label.setText(text)


class ChatPanel(QWidget):
    """Expandable mini chat panel with message history and input."""

    message_submitted = Signal(str)
    new_session_requested = Signal()
    vision_requested = Signal(str)       # "full" or "section"
    settings_requested = Signal()

    PANEL_WIDTH = 320
    PANEL_HEIGHT = 400

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.PANEL_WIDTH, self.PANEL_HEIGHT)

        self._is_visible = False
        self._streaming_bubble: MessageBubble | None = None

        self._setup_ui()
        self.hide()

    # ── Header button styles ──────────────────────────────────────────

    @staticmethod
    def _header_btn_style() -> str:
        return """
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 13px;
                font-size: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(79, 195, 247, 0.2);
                border: 1px solid rgba(79, 195, 247, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(79, 195, 247, 0.4);
            }
        """

    @staticmethod
    def _vision_btn_style() -> str:
        return """
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 13px;
                font-size: 14px;
                padding: 0px;
                color: #F9A825;
            }
            QPushButton:hover {
                background-color: rgba(249, 168, 37, 0.15);
                border: 1px solid rgba(249, 168, 37, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(249, 168, 37, 0.3);
            }
        """

    # ── UI Setup ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # Main container with rounded corners
        self._container = QFrame(self)
        self._container.setStyleSheet("""
            QFrame#chatContainer {
                background-color: rgba(245, 245, 245, 245);
                border-radius: 16px;
                border: 1px solid rgba(200, 200, 200, 180);
            }
        """)
        self._container.setObjectName("chatContainer")
        self._container.setGeometry(0, 0, self.PANEL_WIDTH, self.PANEL_HEIGHT)

        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)

        # ── Header row ──
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 0, 2, 0)
        header_layout.setSpacing(2)

        header_label = QLabel("Pilot Chat")
        header_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header_label.setStyleSheet(
            "background: transparent; color: #333; padding: 4px 0px;"
        )
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # New session button
        new_session_btn = QPushButton("🔄")
        new_session_btn.setFixedSize(26, 26)
        new_session_btn.setToolTip("New Session")
        new_session_btn.setStyleSheet(self._header_btn_style())
        new_session_btn.clicked.connect(self.new_session_requested.emit)
        header_layout.addWidget(new_session_btn)

        # Vision button (yellow eye)
        vision_btn = QPushButton("👁")
        vision_btn.setFixedSize(26, 26)
        vision_btn.setToolTip("Vision — Analyze Screen")
        vision_btn.setStyleSheet(self._vision_btn_style())
        vision_btn.clicked.connect(self._show_vision_menu)
        header_layout.addWidget(vision_btn)

        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(26, 26)
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet(self._header_btn_style())
        settings_btn.clicked.connect(self.settings_requested.emit)
        header_layout.addWidget(settings_btn)

        main_layout.addLayout(header_layout)

        # ── Scroll area for messages ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QWidget#scrollContent {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 40);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self._messages_widget = QWidget()
        self._messages_widget.setObjectName("scrollContent")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(4, 4, 4, 4)
        self._messages_layout.setSpacing(4)
        self._messages_layout.addStretch()

        self._scroll.setWidget(self._messages_widget)
        main_layout.addWidget(self._scroll, 1)

        # ── Token counter ──
        self._token_label = QLabel("")
        self._token_label.setFont(QFont("Segoe UI", 8))
        self._token_label.setStyleSheet(
            "color: #999; background: transparent; padding: 0 8px;"
        )
        self._token_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._token_label.hide()
        main_layout.addWidget(self._token_label)

        # ── Input area ──
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message...")
        self._input.setFont(QFont("Segoe UI", 10))
        self._input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: #1A1A1A;
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 6px 12px;
            }
            QLineEdit:focus {
                border: 1px solid #4FC3F7;
            }
        """)
        self._input.returnPressed.connect(self._on_submit)
        input_layout.addWidget(self._input, 1)

        send_btn = QPushButton("➤")
        send_btn.setFixedSize(32, 32)
        send_btn.setFont(QFont("Segoe UI", 12))
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4FC3F7;
                color: white;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #03A9F4;
            }
            QPushButton:pressed {
                background-color: #0288D1;
            }
        """)
        send_btn.clicked.connect(self._on_submit)
        input_layout.addWidget(send_btn)

        main_layout.addLayout(input_layout)

    # ── Vision menu ───────────────────────────────────────────────────

    def _show_vision_menu(self) -> None:
        """Show popup with vision capture options."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
                color: #1A1A1A;
            }
            QMenu::item:selected {
                background-color: #FFF8E1;
            }
        """)

        full_action = menu.addAction("🖥  Entire Screen")
        full_action.triggered.connect(lambda: self.vision_requested.emit("full"))

        section_action = menu.addAction("✂  Select Section")
        section_action.triggered.connect(lambda: self.vision_requested.emit("section"))

        # Position menu below the vision button
        menu.exec(self.mapToGlobal(self.rect().topRight()))

    # ── Internal helpers ──────────────────────────────────────────────

    def _add_bubble(self, text: str, role: str) -> MessageBubble:
        bubble = MessageBubble(text, role, self._messages_widget)
        # Insert before the stretch
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the message list."""
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    # ── Public API ────────────────────────────────────────────────────

    def add_user_message(self, text: str) -> None:
        self._add_bubble(text, "user")

    def add_assistant_message(self, text: str) -> None:
        self._add_bubble(text, "assistant")

    def add_tool_message(self, name: str, success: bool | None, summary: str) -> None:
        if success is None:
            icon = "⏳"
        elif success:
            icon = "✅"
        else:
            icon = "❌"
        self._add_bubble(f"{icon} {name}: {summary}", "tool")

    def add_error_message(self, text: str) -> None:
        self._add_bubble(f"❌ {text}", "error")

    def start_streaming(self) -> None:
        """Start a new streaming assistant message."""
        self._streaming_bubble = self._add_bubble("", "assistant")

    def append_streaming(self, text: str) -> None:
        """Append text to the current streaming bubble."""
        if self._streaming_bubble:
            self._streaming_bubble.append_text(text)
            self._scroll_to_bottom()

    def end_streaming(self) -> None:
        """Finalize the streaming bubble."""
        self._streaming_bubble = None
        self._scroll_to_bottom()

    def update_token_count(self, input_tokens: int, output_tokens: int) -> None:
        """Update the token counter display."""
        self._token_label.setText(
            f"Tokens: {input_tokens:,} in / {output_tokens:,} out"
        )
        self._token_label.show()

    def clear(self) -> None:
        """Remove all messages."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def toggle(self) -> None:
        """Show or hide the panel."""
        if self._is_visible:
            self.hide()
            self._is_visible = False
        else:
            self.show()
            self._is_visible = True
            self._input.setFocus()

    def position_beside(self, anchor_global_x: int, anchor_global_y: int, anchor_height: int) -> None:
        """Position panel to the left of the character."""
        x = anchor_global_x - self.PANEL_WIDTH - 10
        y = anchor_global_y + anchor_height // 2 - self.PANEL_HEIGHT // 2

        # Keep on screen
        if x < 10:
            x = anchor_global_x + 130  # Put on right side instead
        if y < 10:
            y = 10

        self.move(x, y)

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.message_submitted.emit(text)
