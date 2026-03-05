"""File operation tools — read, write, edit, glob, grep."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

from pilot.tools.base import BaseTool, ToolParameter, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file. Returns the file content with line numbers."
    parameters = [
        ToolParameter("path", "string", "Absolute or relative path to the file to read"),
        ToolParameter("offset", "integer", "Line number to start reading from (1-based)", required=False),
        ToolParameter("limit", "integer", "Maximum number of lines to read", required=False),
    ]

    async def execute(self, path: str, offset: int | None = None, limit: int | None = None) -> ToolResult:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(success=False, output="", error=f"File not found: {p}")
        if not p.is_file():
            return ToolResult(success=False, output="", error=f"Not a file: {p}")

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()

            start = (offset - 1) if offset and offset > 0 else 0
            end = (start + limit) if limit else len(lines)
            selected = lines[start:end]

            numbered = [f"{i + start + 1:4d} | {line}" for i, line in enumerate(selected)]
            output = "\n".join(numbered)

            return ToolResult(success=True, output=output or "(empty file)")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file. Creates the file and parent directories if they don't exist. Overwrites existing content."
    parameters = [
        ToolParameter("path", "string", "Path to the file to write"),
        ToolParameter("content", "string", "The content to write to the file"),
    ]

    async def execute(self, path: str, content: str) -> ToolResult:
        p = Path(path).resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return ToolResult(success=True, output=f"Written {line_count} lines to {p}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Edit a file by replacing an exact string with new content. The old_string must match exactly (including whitespace)."
    parameters = [
        ToolParameter("path", "string", "Path to the file to edit"),
        ToolParameter("old_string", "string", "The exact text to find and replace"),
        ToolParameter("new_string", "string", "The replacement text"),
    ]

    async def execute(self, path: str, old_string: str, new_string: str) -> ToolResult:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(success=False, output="", error=f"File not found: {p}")

        try:
            text = p.read_text(encoding="utf-8")
            count = text.count(old_string)

            if count == 0:
                return ToolResult(success=False, output="", error="old_string not found in file")
            if count > 1:
                return ToolResult(
                    success=False, output="",
                    error=f"old_string found {count} times — must be unique. Add more context."
                )

            new_text = text.replace(old_string, new_string, 1)
            p.write_text(new_text, encoding="utf-8")
            return ToolResult(success=True, output=f"Edited {p} — replaced 1 occurrence")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GlobFilesTool(BaseTool):
    name = "glob_files"
    description = "Find files matching a glob pattern. Example patterns: '**/*.py', 'src/**/*.ts', '*.json'"
    parameters = [
        ToolParameter("pattern", "string", "Glob pattern to match files (e.g., '**/*.py')"),
        ToolParameter("path", "string", "Directory to search in (default: current directory)", required=False),
    ]

    async def execute(self, pattern: str, path: str | None = None) -> ToolResult:
        base = Path(path).resolve() if path else Path.cwd()
        if not base.exists():
            return ToolResult(success=False, output="", error=f"Directory not found: {base}")

        try:
            matches = sorted(base.glob(pattern))
            # Limit to 200 results
            if len(matches) > 200:
                output = "\n".join(str(m) for m in matches[:200])
                output += f"\n... and {len(matches) - 200} more"
            elif matches:
                output = "\n".join(str(m) for m in matches)
            else:
                output = "No files matched the pattern."

            return ToolResult(success=True, output=f"Found {len(matches)} files:\n{output}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GrepTool(BaseTool):
    name = "grep"
    description = "Search file contents using a regex pattern. Returns matching lines with file paths and line numbers."
    parameters = [
        ToolParameter("pattern", "string", "Regex pattern to search for"),
        ToolParameter("path", "string", "File or directory to search in (default: current directory)", required=False),
        ToolParameter("include", "string", "Glob pattern to filter files (e.g., '*.py')", required=False),
    ]

    async def execute(self, pattern: str, path: str | None = None, include: str | None = None) -> ToolResult:
        base = Path(path).resolve() if path else Path.cwd()

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return ToolResult(success=False, output="", error=f"Invalid regex: {e}")

        results: list[str] = []
        max_results = 100

        try:
            if base.is_file():
                files = [base]
            else:
                files = [f for f in base.rglob("*") if f.is_file()]

            for file_path in files:
                if include and not fnmatch.fnmatch(file_path.name, include):
                    continue

                # Skip binary files and large files
                if file_path.stat().st_size > 1_000_000:
                    continue

                try:
                    text = file_path.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{i}: {line.rstrip()}")
                            if len(results) >= max_results:
                                break
                except (PermissionError, OSError):
                    continue

                if len(results) >= max_results:
                    break

            if results:
                output = "\n".join(results)
                if len(results) >= max_results:
                    output += f"\n... (limited to {max_results} results)"
                return ToolResult(success=True, output=output)
            else:
                return ToolResult(success=True, output="No matches found.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
