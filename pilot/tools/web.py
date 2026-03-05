"""Web fetching and scraping tools."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from pilot.tools.base import BaseTool, ToolParameter, ToolResult


class FetchURLTool(BaseTool):
    name = "fetch_url"
    description = "Fetch the content of a URL. Returns the raw text or HTML content."
    parameters = [
        ToolParameter("url", "string", "The URL to fetch"),
    ]

    async def execute(self, url: str) -> ToolResult:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Pilot-Agent/0.1"
                })
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                text = resp.text

                # Truncate large responses
                if len(text) > 50000:
                    text = text[:50000] + "\n... (truncated)"

                return ToolResult(
                    success=True,
                    output=f"[{resp.status_code}] {content_type}\n\n{text}"
                )
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, output="", error=f"HTTP {e.response.status_code}: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ScrapePageTool(BaseTool):
    name = "scrape_page"
    description = (
        "Fetch a web page and extract its text content, stripping HTML tags. "
        "Optionally filter by CSS selector."
    )
    parameters = [
        ToolParameter("url", "string", "The URL to scrape"),
        ToolParameter("selector", "string", "CSS selector to filter elements (e.g., 'article', '.content')", required=False),
    ]

    async def execute(self, url: str, selector: str | None = None) -> ToolResult:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Pilot-Agent/0.1"
                })
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            if selector:
                elements = soup.select(selector)
                if not elements:
                    return ToolResult(success=True, output=f"No elements matched selector: {selector}")
                text = "\n\n".join(el.get_text(strip=True, separator="\n") for el in elements)
            else:
                text = soup.get_text(strip=True, separator="\n")

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)

            if len(text) > 30000:
                text = text[:30000] + "\n... (truncated)"

            return ToolResult(success=True, output=text or "(no text content found)")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
