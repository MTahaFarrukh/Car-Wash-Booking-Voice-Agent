"""Fake LLM provider for automated tests."""

from __future__ import annotations

from collections.abc import Callable

from app.llm.base import LLMProvider
from app.llm.schemas import LLMCompletionResult, LLMMessage, LLMToolSpec


ScriptFn = Callable[[list[LLMMessage], list[LLMToolSpec] | None], LLMCompletionResult]


class FakeLLMProvider(LLMProvider):
    """Scripted provider that never makes network calls."""

    def __init__(self, scripts: list[ScriptFn] | None = None) -> None:
        self._scripts = list(scripts or [])
        self.calls: list[dict] = []

    def queue(self, script: ScriptFn) -> None:
        self._scripts.append(script)

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        return self._next(messages, None)

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        return self._next(messages, tools)

    def _next(self, messages: list[LLMMessage], tools: list[LLMToolSpec] | None) -> LLMCompletionResult:
        self.calls.append({"messages": messages, "tools": tools})
        if not self._scripts:
            return LLMCompletionResult(content="Sorry, I'm having trouble processing that right now. Please try again in a moment.")
        script = self._scripts.pop(0)
        return script(messages, tools)
