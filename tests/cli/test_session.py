from datetime import UTC, datetime

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
