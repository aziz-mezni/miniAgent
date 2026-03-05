"""Desktop application control tools using pyautogui."""

from __future__ import annotations

import asyncio
import base64
import io
import os
import subprocess
import sys
from pathlib import Path

from pilot.tools.base import BaseTool, ToolParameter, ToolResult


class OpenAppTool(BaseTool):
    name = "open_app"
    description = "Open a desktop application by name or path. Examples: 'notepad', 'code', 'chrome', or a full path."
    parameters = [
        ToolParameter("name_or_path", "string", "Application name (e.g., 'notepad', 'code') or full path"),
    ]

    async def execute(self, name_or_path: str) -> ToolResult:
        try:
            if sys.platform == "win32":
                # Try os.startfile first for Windows
                try:
                    os.startfile(name_or_path)
                    return ToolResult(success=True, output=f"Opened: {name_or_path}")
                except OSError:
                    # Fall back to subprocess
                    proc = await asyncio.create_subprocess_shell(
                        f"start \"\" \"{name_or_path}\"",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.communicate()
                    return ToolResult(success=True, output=f"Opened: {name_or_path}")
            elif sys.platform == "darwin":
                proc = await asyncio.create_subprocess_exec(
                    "open", name_or_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return ToolResult(success=True, output=f"Opened: {name_or_path}")
            else:
                proc = await asyncio.create_subprocess_exec(
                    "xdg-open", name_or_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return ToolResult(success=True, output=f"Opened: {name_or_path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = "Take a screenshot of the screen or a specific region. Returns the image as a base64 string."
    parameters = [
        ToolParameter(
            "region", "string",
            "Region to capture as 'x,y,width,height' (e.g., '0,0,800,600'). Omit for full screen.",
            required=False
        ),
    ]

    async def execute(self, region: str | None = None) -> ToolResult:
        try:
            import pyautogui

            if region:
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) != 4:
                    return ToolResult(success=False, output="", error="Region must be 'x,y,width,height'")
                img = pyautogui.screenshot(region=tuple(parts))
            else:
                img = pyautogui.screenshot()

            # Save to buffer
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            return ToolResult(
                success=True,
                output=f"Screenshot captured ({img.width}x{img.height}). Base64 length: {len(b64)}"
            )
        except ImportError:
            return ToolResult(success=False, output="", error="pyautogui not installed")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ClickTool(BaseTool):
    name = "click"
    description = "Click the mouse at specific screen coordinates."
    parameters = [
        ToolParameter("x", "integer", "X coordinate (pixels from left)"),
        ToolParameter("y", "integer", "Y coordinate (pixels from top)"),
        ToolParameter("button", "string", "Mouse button: 'left', 'right', or 'middle'", required=False),
        ToolParameter("clicks", "integer", "Number of clicks (default: 1)", required=False),
    ]

    async def execute(
        self, x: int, y: int, button: str = "left", clicks: int = 1
    ) -> ToolResult:
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return ToolResult(success=True, output=f"Clicked ({x}, {y}) button={button} clicks={clicks}")
        except ImportError:
            return ToolResult(success=False, output="", error="pyautogui not installed")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class TypeTextTool(BaseTool):
    name = "type_text"
    description = "Type text using the keyboard. Simulates keypresses."
    parameters = [
        ToolParameter("text", "string", "The text to type"),
        ToolParameter("interval", "number", "Seconds between keystrokes (default: 0.02)", required=False),
    ]

    async def execute(self, text: str, interval: float = 0.02) -> ToolResult:
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            return ToolResult(success=True, output=f"Typed {len(text)} characters")
        except ImportError:
            return ToolResult(success=False, output="", error="pyautogui not installed")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class HotkeyTool(BaseTool):
    name = "hotkey"
    description = "Press a keyboard shortcut. Examples: 'ctrl+s', 'alt+tab', 'ctrl+shift+p'"
    parameters = [
        ToolParameter("keys", "string", "Key combination separated by '+' (e.g., 'ctrl+s', 'alt+f4')"),
    ]

    async def execute(self, keys: str) -> ToolResult:
        try:
            import pyautogui
            key_list = [k.strip() for k in keys.split("+")]
            pyautogui.hotkey(*key_list)
            return ToolResult(success=True, output=f"Pressed: {keys}")
        except ImportError:
            return ToolResult(success=False, output="", error="pyautogui not installed")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
