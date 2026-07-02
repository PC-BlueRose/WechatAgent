import sys
from datetime import UTC, datetime

from wechat_agent.cli.app import _configure_console_output, main, run_cli_once
from wechat_agent.cli.session import build_cli_session


def test_run_cli_once_routes_plain_text_to_agent_reply():
    session = build_cli_session()

    output, should_exit = run_cli_once(
        session,
        "I slept around 2 and woke up tired.",
        now=datetime(2026, 7, 2, 8, 0, tzinfo=UTC),
    )

    assert should_exit is False
    assert "Take your time" in output


def test_run_cli_once_preserves_plain_text_whitespace_for_agent():
    class StubSession:
        def __init__(self) -> None:
            self.received: list[tuple[str, datetime | None]] = []

        def handle_text(self, text: str, now: datetime | None = None) -> str:
            self.received.append((text, now))
            return "ok"

    session = StubSession()
    timestamp = datetime(2026, 7, 2, 8, 0, tzinfo=UTC)

    output, should_exit = run_cli_once(session, "  hello there  ", now=timestamp)

    assert should_exit is False
    assert output == "ok"
    assert session.received == [("  hello there  ", timestamp)]


def test_run_cli_once_routes_slash_command_through_command_engine():
    session = build_cli_session()

    output, should_exit = run_cli_once(
        session,
        "/mode quiet",
        now=datetime(2026, 7, 2, 8, 1, tzinfo=UTC),
    )

    assert should_exit is False
    assert output == "Mode set to quiet."


def test_run_cli_once_marks_exit_command():
    session = build_cli_session()

    output, should_exit = run_cli_once(
        session,
        "/exit",
        now=datetime(2026, 7, 2, 8, 2, tzinfo=UTC),
    )

    assert should_exit is True
    assert output == "Bye."


def test_run_cli_once_returns_state_summary_for_state_command():
    session = build_cli_session()

    output, should_exit = run_cli_once(
        session,
        "/state",
        now=datetime(2026, 7, 2, 8, 3, tzinfo=UTC),
    )

    assert should_exit is False
    assert "Mode: daily" in output
    assert "Recent events:" in output


def test_run_cli_once_normalizes_whitespace_before_command_routing():
    session = build_cli_session()

    output, should_exit = run_cli_once(
        session,
        "  /mode quiet  ",
        now=datetime(2026, 7, 2, 8, 3, tzinfo=UTC),
    )

    assert should_exit is False
    assert output == "Mode set to quiet."


def test_main_prints_startup_banner_and_exits_on_eof(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError()))

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "WechatAgent CLI ready. Use /help for commands.\nBye.\n"


def test_main_skips_blank_lines_and_prefixes_agent_output(monkeypatch, capsys):
    session = build_cli_session()
    inputs = iter(["   ", "I slept around 2 and woke up tired.", "/exit"])

    monkeypatch.setattr("wechat_agent.cli.app.build_cli_session", lambda: session)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("WechatAgent CLI ready. Use /help for commands.\n")
    assert "Agent: " in captured.out
    assert "Take your time" in captured.out
    assert captured.out.rstrip().endswith("Bye.")


def test_main_does_not_prefix_whitespace_padded_slash_command_output(
    monkeypatch, capsys
):
    session = build_cli_session()
    inputs = iter(["  /mode quiet  ", "/exit"])

    monkeypatch.setattr("wechat_agent.cli.app.build_cli_session", lambda: session)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Mode set to quiet." in captured.out
    assert "Agent: Mode set to quiet." not in captured.out


def test_configure_console_output_reconfigures_stdout_and_stderr(monkeypatch):
    calls: list[tuple[str, dict[str, str]]] = []

    class StubStream:
        def __init__(self, name: str) -> None:
            self.name = name

        def reconfigure(self, **kwargs: str) -> None:
            calls.append((self.name, kwargs))

    monkeypatch.setattr(sys, "stdout", StubStream("stdout"))
    monkeypatch.setattr(sys, "stderr", StubStream("stderr"))

    _configure_console_output()

    assert calls == [
        ("stdout", {"errors": "replace"}),
        ("stderr", {"errors": "replace"}),
    ]
