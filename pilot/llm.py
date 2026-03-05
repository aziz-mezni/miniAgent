"""LLM client — OpenAI-compatible API with streaming support."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from pilot.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """A single tool call from the LLM."""
    id: str
    name: str
    arguments: str  # JSON string

    def parsed_arguments(self) -> dict[str, Any]:
        try:
            return json.loads(self.arguments)
        except json.JSONDecodeError:
            return {}


@dataclass
class LLMResponse:
    """Complete response from the LLM."""
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class StreamDelta:
    """A single delta from streaming."""
    content: str | None = None
    tool_call_index: int | None = None
    tool_call_id: str | None = None
    tool_call_name: str | None = None
    tool_call_arguments: str | None = None
    finish_reason: str | None = None


class LLMClient:
    """Client for OpenAI-compatible LLM APIs."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.api.base_url,
            api_key=config.api.api_key,
        )
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamDelta, None]:
        """Stream a chat completion, yielding deltas."""
        kwargs: dict[str, Any] = {
            "model": self.config.api.model,
            "messages": messages,
            "temperature": self.config.agent.temperature,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self.client.chat.completions.create(**kwargs)

            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue

                delta = choice.delta
                stream_delta = StreamDelta(finish_reason=choice.finish_reason)

                if delta.content:
                    stream_delta.content = delta.content

                if delta.tool_calls:
                    tc = delta.tool_calls[0]
                    stream_delta.tool_call_index = tc.index
                    if tc.id:
                        stream_delta.tool_call_id = tc.id
                    if tc.function:
                        if tc.function.name:
                            stream_delta.tool_call_name = tc.function.name
                        if tc.function.arguments:
                            stream_delta.tool_call_arguments = tc.function.arguments

                # Track usage if available
                if hasattr(chunk, "usage") and chunk.usage:
                    self.total_input_tokens += chunk.usage.prompt_tokens or 0
                    self.total_output_tokens += chunk.usage.completion_tokens or 0

                yield stream_delta

        except Exception as e:
            logger.exception("LLM streaming error")
            raise

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Non-streaming chat completion. Accumulates the full response."""
        response = LLMResponse()
        tool_calls_acc: dict[int, dict] = {}  # index -> {id, name, arguments}

        async for delta in self.chat_stream(messages, tools):
            if delta.content:
                if response.content is None:
                    response.content = ""
                response.content += delta.content

            if delta.tool_call_index is not None:
                idx = delta.tool_call_index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}

                if delta.tool_call_id:
                    tool_calls_acc[idx]["id"] = delta.tool_call_id
                if delta.tool_call_name:
                    tool_calls_acc[idx]["name"] = delta.tool_call_name
                if delta.tool_call_arguments:
                    tool_calls_acc[idx]["arguments"] += delta.tool_call_arguments

        # Convert accumulated tool calls
        for idx in sorted(tool_calls_acc.keys()):
            tc = tool_calls_acc[idx]
            response.tool_calls.append(ToolCall(
                id=tc["id"],
                name=tc["name"],
                arguments=tc["arguments"],
            ))

        return response

    async def test_connection(self) -> bool:
        """Test if the LLM API is reachable."""
        try:
            models = await self.client.models.list()
            return True
        except Exception:
            return False
