"""System tray icon with menu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

if TYPE_CHECKING:
    from buddy.main_window import BuddyWindow


def _create_tray_icon() -> QIcon:
    """Create a simple programmatic tray icon (blue circle with face)."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Blue circle
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#4FC3F7")))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # Eyes
    painter.setBrush(QBrush(QColor("white")))
    painter.drawEllipse(18, 20, 10, 10)
    painter.drawEllipse(36, 20, 10, 10)

    # Pupils
    painter.setBrush(QBrush(QColor("#1A237E")))
    painter.drawEllipse(21, 23, 5, 5)
    painter.drawEllipse(39, 23, 5, 5)

    # Smile
    painter.setPen(QPen(QColor("#1A237E"), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(22, 30, 20, 12, 200 * 16, 140 * 16)

    painter.end()
    return QIcon(pixmap)


class BuddyTray(QSystemTrayIcon):
    """System tray icon for the Buddy assistant."""

    def __init__(self, window: BuddyWindow) -> None:
        super().__init__()

        self._window = window

        # Icon
        self.setIcon(_create_tray_icon())
        self.setToolTip("Pilot Buddy — AI Assistant")

        # Menu
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
        """)

        show_action = menu.addAction("👁️ Show / Hide")
        show_action.triggered.connect(self._toggle_window)

        chat_action = menu.addAction("💬 Open Chat")
        chat_action.triggered.connect(self._open_chat)

        menu.addSeparator()

        quit_action = menu.addAction("❌ Quit")
        quit_action.triggered.connect(QApplication.quit)

        self.setContextMenu(menu)

        # Double-click to toggle
        self.activated.connect(self._on_activated)

        self.show()

    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
            self._window.bubble.hide()
            self._window.panel.hide()
        else:
            self._window.show()

    def _open_chat(self) -> None:
        if not self._window.isVisible():
            self._window.show()
        self._window._toggle_panel()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()
