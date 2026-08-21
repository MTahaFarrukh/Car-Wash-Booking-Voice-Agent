"""Abstract LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMCompletionResult, LLMMessage, LLMToolSpec


class LLMProvider(ABC):
    """Provider-independent LLM interface used by conversational agents."""

    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        """Generate a text completion without tools."""

    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        """Generate a completion that may include tool calls."""
