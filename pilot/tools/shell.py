"""Shell command execution tool."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from pilot.tools.base import BaseTool, ToolParameter, ToolResult


class RunCommandTool(BaseTool):
    name = "run_command"
    description = (
        "Execute a shell command and return its output. "
        "Use this for running scripts, installing packages, git operations, "
        "building projects, and any terminal operations."
    )
    parameters = [
        ToolParameter("command", "string", "The shell command to execute"),
        ToolParameter("timeout", "integer", "Timeout in seconds (default: 120)", required=False),
        ToolParameter("cwd", "string", "Working directory for the command", required=False),
    ]

    async def execute(
        self, command: str, timeout: int = 120, cwd: str | None = None
    ) -> ToolResult:
        work_dir = Path(cwd).resolve() if cwd else Path.cwd()

        if not work_dir.exists():
            return ToolResult(success=False, output="", error=f"Directory not found: {work_dir}")

        try:
            # Use asyncio subprocess for non-blocking execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env={**os.environ},
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return ToolResult(
                    success=False, output="",
                    error=f"Command timed out after {timeout}s: {command}"
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            # Truncate very long outputs
            max_len = 30000
            if len(stdout) > max_len:
                stdout = stdout[:max_len] + f"\n... (truncated, {len(stdout)} total chars)"
            if len(stderr) > max_len:
                stderr = stderr[:max_len] + f"\n... (truncated, {len(stderr)} total chars)"

            exit_code = process.returncode

            parts = []
            if stdout:
                parts.append(stdout)
            if stderr:
                parts.append(f"[stderr]\n{stderr}")
            parts.append(f"[exit code: {exit_code}]")

            output = "\n".join(parts)

            return ToolResult(
                success=(exit_code == 0),
                output=output,
                error=f"Command failed with exit code {exit_code}" if exit_code != 0 else None,
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
