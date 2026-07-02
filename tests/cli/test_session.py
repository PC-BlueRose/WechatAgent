from datetime import UTC, datetime

from wechat_agent.llm.minimax_gateway import MiniMaxLLMGateway
from wechat_agent.cli.session import build_cli_session


def test_format_state_uses_none_when_session_is_empty():
    session = build_cli_session()

    output = session.format_state(now=datetime(2026, 7, 2, 8, 0, tzinfo=UTC))

    assert output == "\n".join(
        [
            "Mode: daily",
            "Active memories: 0",
            "Tasks: none",
            "Recent events:",
            "- none",
        ]
    )


def test_format_state_counts_tasks_by_status():
    session = build_cli_session()
    session.handle_text(
        "Remind me tomorrow morning to stretch.",
        now=datetime(2026, 7, 2, 22, 0, tzinfo=UTC),
    )
    session.send_due_tasks(now=datetime(2026, 7, 3, 8, 0, tzinfo=UTC))
    session.handle_text(
        "Remind me tomorrow morning to hydrate.",
        now=datetime(2026, 7, 3, 22, 0, tzinfo=UTC),
    )

    output = session.format_state(now=datetime(2026, 7, 3, 22, 1, tzinfo=UTC))

    assert "Tasks: pending=1, sent=1" in output


def test_build_cli_session_uses_fake_gateway_by_default(monkeypatch):
    for name in (
        "WECHAT_AGENT_LLM_PROVIDER",
        "WECHAT_AGENT_MINIMAX_API_KEY",
        "WECHAT_AGENT_MINIMAX_BASE_URL",
        "WECHAT_AGENT_MINIMAX_CHAT_MODEL",
        "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL",
        "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL",
        "WECHAT_AGENT_MINIMAX_VISION_MODEL",
        "WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS",
        "WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK",
    ):
        monkeypatch.delenv(name, raising=False)

    session = build_cli_session()

    assert session.orchestrator._llm.__class__.__name__ == "FakeLLMGateway"


def test_build_cli_session_uses_minimax_gateway_when_configured(monkeypatch):
    monkeypatch.setenv("WECHAT_AGENT_LLM_PROVIDER", "minimax")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_API_KEY", "test-key")

    session = build_cli_session()

    assert isinstance(session.orchestrator._llm, MiniMaxLLMGateway)
