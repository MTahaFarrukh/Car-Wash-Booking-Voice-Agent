"""Shared LLM provider errors."""

from __future__ import annotations


class LLMProviderError(Exception):
    """Raised when an LLM provider request fails."""


class GeminiProviderError(LLMProviderError):
    """Raised for Gemini-specific provider failures."""
