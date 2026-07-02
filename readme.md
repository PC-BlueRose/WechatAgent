# WechatAgent

WechatAgent is a channel-independent personal life Agent prototype.

The first implementation target is a modular Python monolith with:

- normalized message adapters
- Agent orchestration
- memory and life event extraction
- daily scheduling
- quiet, daily, and coach modes
- an LLM gateway abstraction
- a deterministic test channel
- a local CLI test harness

The first runnable channel is `TestChannelAdapter`; direct personal WeChat integration is intentionally deferred until the core Agent behavior is stable.

## Runtime Baselines

- Python 3.12.10
- PostgreSQL 16

## Development

Install in editable mode:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -v
```

## CLI

Start the local CLI:

```bash
wechat-agent-cli
```

Type any plain-text message at the prompt to chat with the Agent through the in-memory test harness.

## MiniMax Setup

The CLI defaults to the deterministic fake gateway. To run against MiniMax, set:

```bash
WECHAT_AGENT_LLM_PROVIDER=minimax
WECHAT_AGENT_MINIMAX_API_KEY=your-key
WECHAT_AGENT_MINIMAX_BASE_URL=https://api.minimax.io/v1
WECHAT_AGENT_MINIMAX_CHAT_MODEL=MiniMax-M3
WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL=MiniMax-M3
WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL=MiniMax-Embedding-01
WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK=true
```

Available commands:

- `/help`
- `/mode quiet|daily|coach`
- `/checkin morning|lunch|afternoon|evening|bedtime`
- `/due now`
- `/state`
- `/exit`

The CLI is an in-memory MVP test harness for plain-text chat, reminders, mode switching, and proactive check-ins.
