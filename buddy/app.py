"""Application setup — QApplication + qasync event loop + startup."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

import qasync

from pilot.config import Config
from pilot.agent import Agent
from pilot.tool_registry import create_default_registry

from buddy.main_window import BuddyWindow
from buddy.bridge import BuddyBridge, BuddyRenderer
from buddy.tray import BuddyTray


class BuddyApp:
    """Main application — bridges Qt and asyncio via qasync."""

    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)  # Keep alive via tray

        # Bridge Qt ↔ asyncio
        self.loop = qasync.QEventLoop(self.qt_app)
        asyncio.set_event_loop(self.loop)

        self.window: BuddyWindow | None = None
        self.tray: BuddyTray | None = None

    async def startup(self) -> None:
        """Initialize agent, create GUI, test connection."""
        # Load config (same config.yaml as Pilot)
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = Config.load(config_path)

        # Create agent with all tools
        registry = create_default_registry()
        agent = Agent(config, registry)

        # Create window
        self.window = BuddyWindow()

        # Create bridge (duck-types Terminal for agent.py)
        renderer = BuddyRenderer(
            self.window.character,
            self.window.bubble,
            self.window.panel,
        )
        bridge = BuddyBridge(renderer)

        # Wire up
        self.window.agent = agent
        self.window.bridge = bridge

        # System tray
        self.tray = BuddyTray(self.window)

        # Show window
        self.window.show()

        # Test connection
        try:
            connected = await agent.llm.test_connection()
            if connected:
                model = config.api.model
                self.window.bubble.show_message(
                    f"✅ Connected to {model}!\nClick me to chat.",
                    duration=5000,
                )
                self.window.character.set_state("wave")
                # Return to idle after wave
                await asyncio.sleep(2)
                self.window.character.set_state("idle")
            else:
                self.window.bubble.show_message(
                    f"❌ Can't reach LLM at {config.api.base_url}\n"
                    "Start your LLM server and restart.",
                    duration=10000,
                )
                self.window.character.set_state("error")
        except Exception as e:
            self.window.bubble.show_message(
                f"❌ Connection error: {e}",
                duration=10000,
            )

    def run(self) -> None:
        """Run the application."""
        with self.loop:
            self.loop.run_until_complete(self.startup())
            self.loop.run_forever()
