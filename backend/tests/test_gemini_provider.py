"""Unit tests for Gemini provider (no real API calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.llm.errors import GeminiProviderError, LLMProviderError
from app.llm.gemini_provider import DEFAULT_GEMINI_MODEL, GeminiProvider
from app.llm.provider import create_llm_provider
from app.llm.schemas import LLMMessage, LLMToolCall, LLMToolSpec


def _gemini_text_body(text: str) -> dict:
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": text}]},
                "finishReason": "STOP",
            }
        ]
    }


def _gemini_tool_body(name: str, args: dict, call_id: str = "fc1") -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {
                            "functionCall": {
                                "name": name,
                                "args": args,
                                "id": call_id,
                            }
                        }
                    ],
                },
                "finishReason": "STOP",
            }
        ]
    }


def _mock_response(status_code: int, body: dict | str) -> httpx.Response:
    content = body if isinstance(body, str) else json.dumps(body)
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/x:generateContent")
    return httpx.Response(status_code, text=content, request=request)


class TestGeminiProvider:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="Gemini API key"):
            GeminiProvider(api_key="")

    def test_default_model(self):
        provider = GeminiProvider(api_key="test-key")
        assert provider.model == DEFAULT_GEMINI_MODEL
        assert DEFAULT_GEMINI_MODEL == "gemini-2.5-flash"

    def test_text_response_parsing(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.return_value = _mock_response(200, _gemini_text_body("Hello from Gemini"))
            result = provider.complete([LLMMessage(role="user", content="Hi")])
        assert result.content == "Hello from Gemini"
        assert result.tool_calls == []

    def test_tool_call_parsing(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.return_value = _mock_response(
                200,
                _gemini_tool_body("list_services", {"active_only": True}),
            )
            result = provider.complete_with_tools(
                [LLMMessage(role="user", content="services?")],
                [LLMToolSpec(name="list_services", description="List services", parameters={"type": "object"})],
            )
        assert result.has_tool_calls
        assert result.tool_calls[0].name == "list_services"
        assert result.tool_calls[0].arguments["active_only"] is True

    def test_serializes_system_and_tool_messages(self):
        provider = GeminiProvider(api_key="test-key")
        messages = [
            LLMMessage(role="system", content="You are a booking agent."),
            LLMMessage(role="user", content="Book a wash"),
            LLMMessage(
                role="assistant",
                content=None,
                tool_calls=[LLMToolCall(id="1", name="list_services", arguments={"active_only": True})],
            ),
            LLMMessage(
                role="tool",
                name="list_services",
                tool_call_id="1",
                content=json.dumps({"success": True, "data": {"services": []}}),
            ),
        ]
        system, contents = provider._serialize_messages(messages)
        assert "booking agent" in system
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"
        assert "functionCall" in contents[1]["parts"][0]
        assert contents[2]["role"] == "user"
        assert "functionResponse" in contents[2]["parts"][0]

    def test_schema_cleaning_removes_unsupported_keys(self):
        provider = GeminiProvider(api_key="test-key")
        cleaned = provider._clean_parameters_schema(
            {
                "title": "Input",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "email": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "title": "Email",
                    }
                },
            }
        )
        assert "title" not in cleaned
        assert "$schema" not in cleaned
        assert "additionalProperties" not in cleaned
        assert cleaned["properties"]["email"]["type"] == "string"

    def test_invalid_api_key_error(self):
        provider = GeminiProvider(api_key="bad")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.return_value = _mock_response(401, {"error": {"message": "API key not valid"}})
            with pytest.raises(GeminiProviderError, match="Invalid Gemini API key"):
                provider.complete([LLMMessage(role="user", content="Hi")])

    def test_unavailable_model_error(self):
        provider = GeminiProvider(api_key="test-key", model="gemini-does-not-exist")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.return_value = _mock_response(404, {"error": {"message": "model not found"}})
            with pytest.raises(GeminiProviderError, match="model unavailable"):
                provider.complete([LLMMessage(role="user", content="Hi")])

    def test_rate_limit_error(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.return_value = _mock_response(429, {"error": {"message": "quota"}})
            with pytest.raises(GeminiProviderError, match="rate limit"):
                provider.complete([LLMMessage(role="user", content="Hi")])

    def test_malformed_response(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.return_value = _mock_response(200, {"candidates": []})
            with pytest.raises(GeminiProviderError, match="no candidates"):
                provider.complete([LLMMessage(role="user", content="Hi")])

    def test_timeout_error(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.post.side_effect = httpx.TimeoutException("timeout")
            with pytest.raises(GeminiProviderError, match="timed out"):
                provider.complete([LLMMessage(role="user", content="Hi")])


class TestProviderSelection:
    def test_missing_gemini_key_returns_none(self):
        settings = Settings.model_construct(
            llm_provider="gemini",
            gemini_api_key="",
            llm_api_key="",
        )
        assert create_llm_provider(settings) is None

    def test_gemini_provider_selected(self):
        settings = Settings.model_construct(
            llm_provider="gemini",
            gemini_api_key="gemini-test-key",
            gemini_model="gemini-2.5-flash",
            llm_temperature=0.2,
            llm_max_tokens=500,
            llm_timeout_seconds=30,
        )
        provider = create_llm_provider(settings)
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "gemini-test-key"
        assert provider.model == "gemini-2.5-flash"

    def test_openai_still_works_when_selected(self):
        settings = Settings.model_construct(
            llm_provider="openai",
            llm_api_key="openai-test-key",
            llm_model="gpt-4o-mini",
            llm_base_url="https://api.openai.com/v1",
            llm_temperature=0.3,
            llm_max_tokens=800,
            llm_timeout_seconds=45,
            gemini_api_key="",
        )
        from app.llm.openai_provider import OpenAIProvider

        provider = create_llm_provider(settings)
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "openai-test-key"

    def test_openai_not_required_for_gemini(self):
        settings = Settings.model_construct(
            llm_provider="gemini",
            gemini_api_key="gemini-key",
            gemini_model="gemini-2.5-flash",
            llm_api_key="",
            llm_temperature=0.3,
            llm_max_tokens=800,
            llm_timeout_seconds=45,
        )
        assert settings.llm_is_configured is True
        assert create_llm_provider(settings) is not None

    def test_gemini_error_is_llm_provider_error(self):
        assert issubclass(GeminiProviderError, LLMProviderError)
