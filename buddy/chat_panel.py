"""Mini chat panel — expandable chat with input field and message history."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
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
            align = Qt.AlignmentFlag.AlignRight
        elif role == "tool":
            bg = "#FFF3E0"
            align = Qt.AlignmentFlag.AlignLeft
        elif role == "error":
            bg = "#FFCDD2"
            align = Qt.AlignmentFlag.AlignLeft
        else:  # assistant
            bg = "#FFFFFF"
            align = Qt.AlignmentFlag.AlignLeft

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

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def append_text(self, text: str) -> None:
        self._label.setText(self._label.text() + text)

    def set_text(self, text: str) -> None:
        self._label.setText(text)


class ChatPanel(QWidget):
    """Expandable mini chat panel with message history and input."""

    message_submitted = Signal(str)

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

        # ── Header ──
        header = QLabel("💬 Pilot Chat")
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(
            "background: transparent; color: #333; padding: 4px 8px;"
        )
        main_layout.addWidget(header)

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

        # ── Input area ──
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message...")
        self._input.setFont(QFont("Segoe UI", 10))
        self._input.setStyleSheet("""
            QLineEdit {
                background-color: white;
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

    def _add_bubble(self, text: str, role: str) -> MessageBubble:
        bubble = MessageBubble(text, role, self._messages_widget)
        # Insert before the stretch
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the message list."""
        from PySide6.QtCore import QTimer
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
