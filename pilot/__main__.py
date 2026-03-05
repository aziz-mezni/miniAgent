"""Entry point for Pilot agent — python -m pilot"""

import asyncio
import logging
import sys
from pathlib import Path

from pilot.config import Config
from pilot.agent import Agent
from pilot.tool_registry import create_default_registry
from pilot.ui.terminal import Terminal


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def main() -> None:
    setup_logging()

    # Load config
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = Config.load(config_path)

    # Create agent
    registry = create_default_registry()
    agent = Agent(config, registry)

    # Create terminal UI
    terminal = Terminal()

    # Run the main loop
    try:
        asyncio.run(terminal.run(agent))
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
