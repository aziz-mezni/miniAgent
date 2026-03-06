"""Full-screen transparent overlay for screenshot region selection."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import (
    QColor, QPainter, QBrush, QPen, QCursor, QGuiApplication, QFont,
)
from PySide6.QtWidgets import QWidget


class ScreenshotOverlay(QWidget):
    """Transparent full-screen overlay where user draws a selection rectangle.

    Usage:
        overlay = ScreenshotOverlay()
        overlay.region_selected.connect(on_region)
        overlay.selection_cancelled.connect(on_cancel)
        overlay.start_selection()
    """

    region_selected = Signal(QRect)
    selection_cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._start_pos: QPoint | None = None
        self._current_pos: QPoint | None = None
        self._selecting = False

    def start_selection(self) -> None:
        """Show the overlay covering the primary screen."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.virtualGeometry()
            self.setGeometry(geo)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    # ── Painting ──────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

        if self._selecting and self._start_pos and self._current_pos:
            selection = QRect(self._start_pos, self._current_pos).normalized()

            # Clear the selection area (make it brighter)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(selection, Qt.GlobalColor.transparent)

            # Draw border around selection
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.setPen(QPen(QColor("#4FC3F7"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(selection)

            # Dimension label
            w, h = selection.width(), selection.height()
            label = f"{w} × {h}"
            painter.setPen(QPen(QColor("white")))
            painter.setFont(QFont("Segoe UI", 9))

            lx = selection.right() - 70
            ly = selection.bottom() + 18
            # Background behind label
            painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(lx - 4, ly - 14, 78, 20, 4, 4)
            painter.setPen(QPen(QColor("white")))
            painter.drawText(lx, ly, label)

        # Instruction text at top center
        if not self._selecting:
            painter.setPen(QPen(QColor("white")))
            painter.setFont(QFont("Segoe UI", 12))
            painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
            text = "Click and drag to select a region • Esc to cancel"
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(text)
            cx = self.width() // 2 - tw // 2
            cy = 60
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(cx - 12, cy - 18, tw + 24, 30, 8, 8)
            painter.setPen(QPen(QColor("white")))
            painter.drawText(cx, cy, text)

        painter.end()

    # ── Mouse events ──────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._selecting = True

    def mouseMoveEvent(self, event) -> None:
        if self._selecting:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            if self._start_pos and self._current_pos:
                rect = QRect(self._start_pos, self._current_pos).normalized()
                if rect.width() > 10 and rect.height() > 10:
                    self.hide()
                    self.region_selected.emit(rect)
                    return
            # Too small or invalid — cancel
            self.hide()
            self.selection_cancelled.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._selecting = False
            self.hide()
            self.selection_cancelled.emit()
