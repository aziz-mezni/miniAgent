"""Speech bubble widget — appears above the character."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QRect, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QBrush, QPen, QFont, QFontMetrics,
)
from PySide6.QtWidgets import QWidget


class ChatBubble(QWidget):
    """Floating speech bubble with auto-hide and triangle pointer."""

    MAX_WIDTH = 300
    PADDING = 12
    RADIUS = 14
    TAIL_SIZE = 10
    BG_COLOR = QColor(255, 255, 255, 240)
    BORDER_COLOR = QColor(200, 200, 200, 180)
    TEXT_COLOR = QColor(30, 30, 30)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput  # Don't steal focus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._text = ""
        self._font = QFont("Segoe UI", 10)
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self.hide()

    def show_message(self, text: str, duration: int = 5000) -> None:
        """Show a message in the bubble for `duration` ms."""
        self._text = text
        self._auto_hide_timer.stop()

        # Calculate size
        fm = QFontMetrics(self._font)
        text_rect = fm.boundingRect(
            QRect(0, 0, self.MAX_WIDTH - self.PADDING * 2, 1000),
            Qt.TextFlag.TextWordWrap,
            self._text,
        )

        bubble_w = min(text_rect.width() + self.PADDING * 2, self.MAX_WIDTH)
        bubble_h = text_rect.height() + self.PADDING * 2 + self.TAIL_SIZE

        self.setFixedSize(max(bubble_w, 60), max(bubble_h, 40))
        self.update()
        self.show()

        if duration > 0:
            self._auto_hide_timer.start(duration)

    def position_above(self, anchor_global_pos: QPointF, anchor_width: int) -> None:
        """Position the bubble above an anchor widget."""
        x = int(anchor_global_pos.x() + anchor_width / 2 - self.width() / 2)
        y = int(anchor_global_pos.y() - self.height() - 5)
        self.move(x, y)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        tail = self.TAIL_SIZE

        # Bubble body (above tail)
        body_rect = QRectF(1, 1, w - 2, h - tail - 2)

        # Background
        path = QPainterPath()
        path.addRoundedRect(body_rect, self.RADIUS, self.RADIUS)
        painter.setPen(QPen(self.BORDER_COLOR, 1.5))
        painter.setBrush(QBrush(self.BG_COLOR))
        painter.drawPath(path)

        # Tail triangle (pointing down)
        tail_path = QPainterPath()
        mid_x = w / 2
        tail_top = h - tail - 1
        tail_path.moveTo(mid_x - 8, tail_top)
        tail_path.lineTo(mid_x, h - 2)
        tail_path.lineTo(mid_x + 8, tail_top)
        tail_path.closeSubpath()

        painter.setPen(QPen(self.BORDER_COLOR, 1.5))
        painter.setBrush(QBrush(self.BG_COLOR))
        painter.drawPath(tail_path)

        # Cover the border where tail meets body
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.BG_COLOR))
        painter.drawRect(QRectF(mid_x - 7, tail_top - 1, 14, 3))

        # Text
        text_rect = QRectF(
            self.PADDING, self.PADDING,
            w - self.PADDING * 2, h - tail - self.PADDING * 2
        )
        painter.setPen(QPen(self.TEXT_COLOR))
        painter.setFont(self._font)
        painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, self._text)

        painter.end()
