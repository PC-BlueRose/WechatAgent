from datetime import UTC, datetime

from wechat_agent.cli.app import main, run_cli_once
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
