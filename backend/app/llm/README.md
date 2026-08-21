# LLM Provider Layer (Phase 7)

Provider-independent LLM abstraction used by the WhatsApp conversation agent.

## Architecture

```
WhatsApp LLM Agent
    ↓
LLMProvider (abstract)
    ↓
OpenAIProvider (httpx) / FakeLLMProvider (tests)
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
| `LLM_PROVIDER` | `openai` | Provider id (`openai`, `none`/`off`/`rule` disables) |
| `LLM_API_KEY` | empty | API key (required for live LLM) |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature |
| `LLM_MAX_TOKENS` | `800` | Max completion tokens |
| `LLM_TIMEOUT_SECONDS` | `45` | HTTP timeout |
| `LLM_MAX_TOOL_CALLS` | `8` | Cap tool calls per inbound message |

## Interface

`LLMProvider` exposes:

- `complete(messages, ...)`
- `complete_with_tools(messages, tools, ...)`

Normalized types live in `app/llm/schemas.py`.

## Tool calling

Tools are exposed as `LLMToolSpec` objects built from Phase 5 Pydantic input schemas.
The WhatsApp agent executes them only through `Phase5ToolExecutor` → `AgentIntegrationService`.

## Error handling

`OpenAIProvider` raises `LLMProviderError` for timeouts, rate limits, HTTP failures, and malformed responses.
The WhatsApp agent catches these and returns a friendly fallback message.

## Tests

Use `FakeLLMProvider` to script completions and tool calls without network access.
