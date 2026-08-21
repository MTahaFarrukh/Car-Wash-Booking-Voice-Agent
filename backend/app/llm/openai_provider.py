"""OpenAI Chat Completions provider (HTTP via httpx)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.llm.base import LLMProvider
from app.llm.schemas import LLMCompletionResult, LLMMessage, LLMToolCall, LLMToolSpec

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Raised when the LLM provider fails."""


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible chat completions with tool calling."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45.0,
        default_temperature: float = 0.3,
        default_max_tokens: int = 800,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        return self._request(
            messages,
            tools=None,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        return self._request(
            messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _request(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[LLMToolSpec] | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> LLMCompletionResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._serialize_message(message) for message in messages],
            "temperature": self.default_temperature if temperature is None else temperature,
            "max_tokens": self.default_max_tokens if max_tokens is None else max_tokens,
        }
        if tools:
            payload["tools"] = [self._serialize_tool(tool) for tool in tools]
            payload["tool_choice"] = "auto"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError("LLM request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("LLM provider is unavailable") from exc

        if response.status_code == 429:
            raise LLMProviderError("LLM rate limit exceeded")
        if response.status_code >= 400:
            logger.warning("LLM provider error status=%s", response.status_code)
            raise LLMProviderError(f"LLM provider returned HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMProviderError("Malformed LLM response") from exc

        return self._parse_response(body)

    @staticmethod
    def _serialize_tool(tool: LLMToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    @staticmethod
    def _serialize_message(message: LLMMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": message.role}
        if message.content is not None:
            payload["content"] = message.content
        if message.name:
            payload["name"] = message.name
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in message.tool_calls
            ]
        return payload

    @staticmethod
    def _parse_response(body: dict[str, Any]) -> LLMCompletionResult:
        choices = body.get("choices") or []
        if not choices:
            raise LLMProviderError("LLM response contained no choices")

        message = choices[0].get("message") or {}
        tool_calls: list[LLMToolCall] = []
        for raw_call in message.get("tool_calls") or []:
            function = raw_call.get("function") or {}
            arguments_raw = function.get("arguments") or "{}"
            try:
                arguments = json.loads(arguments_raw) if isinstance(arguments_raw, str) else dict(arguments_raw)
            except json.JSONDecodeError as exc:
                raise LLMProviderError("Malformed tool call arguments") from exc
            if not isinstance(arguments, dict):
                raise LLMProviderError("Tool call arguments must be an object")
            tool_calls.append(
                LLMToolCall(
                    id=raw_call.get("id") or "",
                    name=function.get("name") or "",
                    arguments=arguments,
                )
            )

        return LLMCompletionResult(
            content=message.get("content"),
            tool_calls=tool_calls,
            finish_reason=choices[0].get("finish_reason"),
            raw=body,
        )
