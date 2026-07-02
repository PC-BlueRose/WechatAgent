from datetime import UTC, datetime

from wechat_agent.cli.commands import run_command
from wechat_agent.cli.session import build_cli_session
from wechat_agent.domain.modes import AgentMode
from wechat_agent.domain.tasks import TaskStatus


def test_mode_command_switches_active_mode():
    session = build_cli_session()

    result = run_command(session, "/mode coach", now=datetime(2026, 7, 2, 9, 0, tzinfo=UTC))

    assert result.output == "Mode set to coach."
    assert session.store.modes.get(session.user_id).mode is AgentMode.COACH


def test_checkin_command_sends_immediate_proactive_message():
    session = build_cli_session()

    result = run_command(
        session,
        "/checkin morning",
        now=datetime(2026, 7, 2, 8, 0, tzinfo=UTC),
    )

    assert "How did you sleep last night" in result.output
    assert session.channel.sent_messages[-1].content == result.output


def test_due_now_delivers_pending_user_reminder():
    session = build_cli_session()
    session.handle_text(
        "Remind me tomorrow morning to stretch.",
        now=datetime(2026, 7, 2, 21, 0, tzinfo=UTC),
    )

    result = run_command(
        session,
        "/due now",
        now=datetime(2026, 7, 3, 8, 0, tzinfo=UTC),
    )

    assert result.output == "stretch."
    due_task = next(iter(session.store.tasks._tasks.values()))
    assert due_task.status is TaskStatus.SENT


def test_state_command_returns_compact_summary():
    session = build_cli_session()
    session.handle_text(
        "I slept around 2 and woke up tired.",
        now=datetime(2026, 7, 2, 8, 30, tzinfo=UTC),
    )

    result = run_command(session, "/state", now=datetime(2026, 7, 2, 8, 31, tzinfo=UTC))

    assert "Mode: daily" in result.output
    assert "Active memories:" in result.output
    assert "Recent events:" in result.output
    assert "sleep @" in result.output


def test_unknown_command_returns_help_hint():
    session = build_cli_session()

    result = run_command(session, "/wat", now=datetime(2026, 7, 2, 9, 0, tzinfo=UTC))

    assert result.output == "Unknown command. Use /help to view available commands."
