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

The first runnable channel is `TestChannelAdapter`; direct personal WeChat integration is intentionally deferred until the core Agent behavior is stable.

## Development

Install in editable mode:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -v
```
