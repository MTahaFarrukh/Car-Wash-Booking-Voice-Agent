# LLM Provider Layer (Phase 7 / 7.1)

Provider-independent LLM abstraction used by the WhatsApp conversation agent.

## Architecture

```
WhatsApp LLM Agent
    ↓
LLMProvider (abstract)
    ↓
GeminiProvider (default) / OpenAIProvider / FakeLLMProvider
    ↓
Tool calls
    ↓
Phase5ToolExecutor
    ↓
AgentIntegrationService
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai`, or `none`/`off`/`rule` |
| `GEMINI_API_KEY` | empty | Gemini developer API key (required for Gemini) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini Flash model |
| `LLM_API_KEY` | empty | OpenAI key (only when `LLM_PROVIDER=openai`) |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model |
| `LLM_BASE_URL` | OpenAI URL | OpenAI-compatible base URL |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature |
| `LLM_MAX_TOKENS` | `800` | Max completion tokens |
| `LLM_TIMEOUT_SECONDS` | `45` | HTTP timeout |
| `LLM_MAX_TOOL_CALLS` | `8` | Cap tool calls per inbound message |

### Google AI Plus vs Gemini API

**Google AI Plus** (consumer Gemini chat subscription) and **Gemini API** (developer key + quota at [Google AI Studio](https://aistudio.google.com/apikey)) are separate systems.

A Google AI Plus subscription does **not** automatically pay for Gemini API usage. This project uses only the developer API key and whatever free/paid API quota belongs to that Google Cloud / AI Studio project.

## Default model

`gemini-2.5-flash` — current Flash-class model suitable for conversational WhatsApp agents with function calling, low latency, and free-tier development. It is **not** Gemini 2.0 Flash.

If your API key cannot access that model, set `GEMINI_MODEL` to another Flash model available to your key (for example a newer stable Flash release). A 404 returns a clear configuration error — the provider does not silently swap models.

## Interface

`LLMProvider` exposes:

- `complete(messages, ...)`
- `complete_with_tools(messages, tools, ...)`

Normalized types live in `app/llm/schemas.py`.

## Tool calling

Tools are exposed as `LLMToolSpec` objects built from Phase 5 Pydantic input schemas.
`GeminiProvider` converts those schemas into Gemini `functionDeclarations` and maps Gemini `functionCall` / `functionResponse` parts back into the shared `LLMMessage` format.

The WhatsApp agent executes tools only through `Phase5ToolExecutor` → `AgentIntegrationService`.

## Error handling

Providers raise `LLMProviderError` / `GeminiProviderError` for timeouts, rate limits, invalid keys, unavailable models, HTTP failures, and malformed responses.
The WhatsApp agent catches these and returns a friendly fallback message.

## Tests

Use `FakeLLMProvider` for end-to-end WhatsApp agent tests (no network).
Use `tests/test_gemini_provider.py` for Gemini request/response unit tests with mocked HTTP.
