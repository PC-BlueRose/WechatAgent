from datetime import UTC, datetime
from pathlib import Path

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
    session = build_cli_session()

    assert session.orchestrator._llm.__class__.__name__ == "FakeLLMGateway"


def test_build_cli_session_uses_minimax_gateway_when_configured():
    Path(".env").write_text(
        "\n".join(
            [
                "WECHAT_AGENT_LLM_PROVIDER=minimax",
                "WECHAT_AGENT_MINIMAX_API_KEY=test-key",
                "WECHAT_AGENT_MINIMAX_BASE_URL=https://api.minimax.io/v1",
                "WECHAT_AGENT_MINIMAX_CHAT_MODEL=chat-model",
                "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL=extract-model",
                "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL=embed-model",
                "WECHAT_AGENT_STORAGE_BACKEND=inmemory",
                "WECHAT_AGENT_DB_HOST=127.0.0.1",
                "WECHAT_AGENT_DB_PORT=5432",
                "WECHAT_AGENT_DB_NAME=wechat_agent",
                "WECHAT_AGENT_DB_USER=postgres",
                "WECHAT_AGENT_DB_PASSWORD=",
            ]
        ),
        encoding="utf-8",
    )

    session = build_cli_session()

    assert isinstance(session.orchestrator._llm, MiniMaxLLMGateway)
