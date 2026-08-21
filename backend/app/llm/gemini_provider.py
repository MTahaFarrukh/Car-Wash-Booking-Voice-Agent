"""Google Gemini generateContent provider (HTTP via httpx)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx

from app.llm.base import LLMProvider
from app.llm.errors import GeminiProviderError
from app.llm.schemas import LLMCompletionResult, LLMMessage, LLMToolCall, LLMToolSpec

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    """Gemini generateContent API with function/tool calling.

    Uses the official Generative Language REST API:
    POST /v1beta/models/{model}:generateContent

    Google AI Plus (consumer chat) and Gemini API developer keys are separate
    systems — this provider only uses GEMINI_API_KEY / developer API quota.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        base_url: str = GEMINI_API_BASE,
        timeout_seconds: float = 45.0,
        default_temperature: float = 0.3,
        default_max_tokens: int = 800,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.model = (model or DEFAULT_GEMINI_MODEL).strip()
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
        return self._request(messages, tools=None, temperature=temperature, max_tokens=max_tokens)

    def complete_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[LLMToolSpec],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult:
        return self._request(messages, tools=tools, temperature=temperature, max_tokens=max_tokens)

    def _request(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[LLMToolSpec] | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> LLMCompletionResult:
        system_text, contents = self._serialize_messages(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.default_temperature if temperature is None else temperature,
                "maxOutputTokens": self.default_max_tokens if max_tokens is None else max_tokens,
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        if tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": self._clean_parameters_schema(tool.parameters),
                        }
                        for tool in tools
                    ]
                }
            ]
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

        url = f"{self.base_url}/models/{self.model}:generateContent"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={
                        "x-goog-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise GeminiProviderError("Gemini request timed out") from exc
        except httpx.HTTPError as exc:
            raise GeminiProviderError("Gemini provider is unavailable") from exc

        return self._handle_http_response(response)

    def _handle_http_response(self, response: httpx.Response) -> LLMCompletionResult:
        if response.status_code == 429:
            raise GeminiProviderError("Gemini rate limit / quota exceeded")
        if response.status_code == 401 or response.status_code == 403:
            raise GeminiProviderError("Invalid Gemini API key")
        if response.status_code == 404:
            raise GeminiProviderError(
                f"Gemini model unavailable: {self.model}. "
                "Set GEMINI_MODEL to a currently supported model for your API key."
            )
        if response.status_code >= 400:
            detail = self._safe_error_detail(response)
            logger.warning("gemini_error status=%s detail=%s", response.status_code, detail)
            raise GeminiProviderError(f"Gemini provider returned HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            raise GeminiProviderError("Malformed Gemini response") from exc

        return self._parse_response(body)

    @staticmethod
    def _safe_error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
            error = body.get("error") or {}
            return str(error.get("message") or response.text[:200])
        except Exception:
            return response.text[:200]

    @staticmethod
    def _clean_parameters_schema(schema: dict[str, Any]) -> dict[str, Any]:
        """Convert JSON Schema from Pydantic into Gemini's OpenAPI-lite subset.

        Gemini rejects `$ref` / `$defs`, so definitions are inlined first.
        """
        defs = schema.get("$defs") or schema.get("definitions") or {}

        def resolve_ref(ref: str) -> Any:
            # Example: "#/$defs/BookingSource"
            name = ref.rsplit("/", 1)[-1]
            target = defs.get(name)
            if target is None:
                return {"type": "string"}
            return inline(target)

        def inline(node: Any) -> Any:
            if isinstance(node, dict):
                if "$ref" in node:
                    return resolve_ref(str(node["$ref"]))
                cleaned: dict[str, Any] = {}
                for key, value in node.items():
                    if key in {
                        "title",
                        "$schema",
                        "$defs",
                        "definitions",
                        "additionalProperties",
                        "examples",
                        "default",
                        "$id",
                        "$ref",
                    }:
                        continue
                    if key == "anyOf":
                        variants = [
                            item
                            for item in value
                            if not (isinstance(item, dict) and item.get("type") == "null")
                        ]
                        if len(variants) == 1:
                            return inline(variants[0])
                        cleaned[key] = inline(value)
                        continue
                    cleaned[key] = inline(value)
                return cleaned
            if isinstance(node, list):
                return [inline(item) for item in node]
            return node

        cleaned = inline({k: v for k, v in schema.items() if k not in {"$defs", "definitions"}})
        if not isinstance(cleaned, dict):
            return {"type": "object", "properties": {}}
        cleaned.setdefault("type", "object")
        return cleaned

    def _serialize_messages(self, messages: list[LLMMessage]) -> tuple[str, list[dict[str, Any]]]:
        system_chunks: list[str] = []
        contents: list[dict[str, Any]] = []

        for message in messages:
            if message.role == "system":
                if message.content:
                    system_chunks.append(message.content)
                continue

            if message.role == "user":
                contents.append({"role": "user", "parts": [{"text": message.content or ""}]})
                continue

            if message.role == "assistant":
                # Gemini 3 requires exact model parts (including thoughtSignature) to be echoed back.
                if message.provider_parts:
                    contents.append({"role": "model", "parts": message.provider_parts})
                    continue
                parts: list[dict[str, Any]] = []
                if message.content:
                    parts.append({"text": message.content})
                for call in message.tool_calls or []:
                    part: dict[str, Any] = {
                        "functionCall": {
                            "name": call.name,
                            "args": call.arguments or {},
                            "id": call.id or str(uuid.uuid4()),
                        }
                    }
                    if call.thought_signature:
                        part["thoughtSignature"] = call.thought_signature
                    parts.append(part)
                if not parts:
                    parts.append({"text": ""})
                contents.append({"role": "model", "parts": parts})
                continue

            if message.role == "tool":
                response_payload: dict[str, Any]
                try:
                    parsed = json.loads(message.content or "{}")
                    response_payload = parsed if isinstance(parsed, dict) else {"result": parsed}
                except json.JSONDecodeError:
                    response_payload = {"result": message.content or ""}
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": message.name or "tool",
                                    "response": response_payload,
                                    **({"id": message.tool_call_id} if message.tool_call_id else {}),
                                }
                            }
                        ],
                    }
                )
                continue

        if not contents:
            contents = [{"role": "user", "parts": [{"text": ""}]}]

        return "\n\n".join(system_chunks).strip(), contents

    def _parse_response(self, body: dict[str, Any]) -> LLMCompletionResult:
        candidates = body.get("candidates") or []
        if not candidates:
            prompt_feedback = body.get("promptFeedback") or {}
            block_reason = prompt_feedback.get("blockReason")
            if block_reason:
                raise GeminiProviderError(f"Gemini blocked the prompt ({block_reason})")
            raise GeminiProviderError("Gemini response contained no candidates")

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        text_chunks: list[str] = []
        tool_calls: list[LLMToolCall] = []

        for part in parts:
            if not isinstance(part, dict):
                continue
            signature = part.get("thoughtSignature") or part.get("thought_signature")
            if "text" in part and part.get("text"):
                text_chunks.append(str(part["text"]))
            function_call = part.get("functionCall")
            if function_call:
                args = function_call.get("args") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError as exc:
                        raise GeminiProviderError("Malformed Gemini tool call arguments") from exc
                if not isinstance(args, dict):
                    raise GeminiProviderError("Gemini tool call arguments must be an object")
                tool_calls.append(
                    LLMToolCall(
                        id=str(function_call.get("id") or uuid.uuid4()),
                        name=str(function_call.get("name") or ""),
                        arguments=args,
                        thought_signature=str(signature) if signature else None,
                    )
                )

        finish_reason = candidates[0].get("finishReason")
        return LLMCompletionResult(
            content="\n".join(text_chunks).strip() or None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            raw=body,
            provider_parts=parts if parts else None,
        )
