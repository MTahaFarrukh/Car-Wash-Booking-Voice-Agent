"""Provider-independent LLM message and tool schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Role = Literal["system", "user", "assistant", "tool"]


class LLMToolCall(BaseModel):
    """A single tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    """One turn in an LLM conversation."""

    role: Role
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[LLMToolCall] | None = None


class LLMToolSpec(BaseModel):
    """Machine-readable tool definition for providers that support function calling."""

    name: str
    description: str
    parameters: dict[str, Any]


class LLMCompletionResult(BaseModel):
    """Normalized completion result from any provider."""

    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)
