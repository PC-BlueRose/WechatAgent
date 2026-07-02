from __future__ import annotations

import sys
from datetime import UTC, datetime

from wechat_agent.cli.commands import run_command
from wechat_agent.cli.session import CliSession, build_cli_session


def _configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="replace")


def run_cli_once(
    session: CliSession, user_input: str, now: datetime | None = None
) -> tuple[str, bool]:
    timestamp = now or datetime.now(UTC)
    normalized_input = user_input.strip()
    if normalized_input.startswith("/"):
        result = run_command(session, normalized_input, now=timestamp)
        return result.output, result.exit_requested
    return session.handle_text(user_input, now=timestamp), False


def main() -> int:
    _configure_console_output()
    session = build_cli_session()
    print("WechatAgent CLI ready. Use /help for commands.")
    while True:
        try:
            user_input = input("> ")
        except EOFError:
            print("Bye.")
            return 0
        except KeyboardInterrupt:
            print("\nBye.")
            return 0

        normalized_input = user_input.strip()
        if not normalized_input:
            continue

        try:
            output, should_exit = run_cli_once(session, user_input)
        except Exception as exc:  # pragma: no cover - interactive safety net
            print(f"Agent error: {exc}")
            continue

        if output:
            prefix = "Agent: " if not normalized_input.startswith("/") else ""
            print(f"{prefix}{output}")

        if should_exit:
            return 0
