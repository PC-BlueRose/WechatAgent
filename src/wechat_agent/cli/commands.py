from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from wechat_agent.cli.session import CHECKIN_TASKS, CliSession
from wechat_agent.domain.modes import AgentMode


HELP_TEXT = "\n".join(
    [
        "/help - show available commands",
        "/mode quiet|daily|coach - switch Agent mode",
        "/checkin morning|lunch|afternoon|evening|bedtime - send an immediate proactive check-in",
        "/due now - deliver due scheduled tasks",
        "/state - show compact session state",
        "/exit - leave the CLI",
    ]
)


@dataclass(frozen=True)
class CommandResult:
    output: str
    exit_requested: bool = False


def run_command(
    session: CliSession, raw_input: str, now: datetime | None = None
) -> CommandResult:
    timestamp = now or datetime.now(UTC)
    parts = raw_input.strip().split()
    if not parts:
        return CommandResult(output="")

    command = parts[0]
    if command == "/help":
        return CommandResult(output=HELP_TEXT)
    if command == "/exit":
        return CommandResult(output="Bye.", exit_requested=True)
    if command == "/state":
        return CommandResult(output=session.format_state(now=timestamp))
    if command == "/mode":
        if len(parts) != 2 or parts[1] not in {"quiet", "daily", "coach"}:
            return CommandResult(output="Usage: /mode quiet|daily|coach")
        mode = AgentMode(parts[1])
        session.set_mode(mode, now=timestamp)
        return CommandResult(output=f"Mode set to {mode.value}.")
    if command == "/checkin":
        if len(parts) != 2 or parts[1] not in CHECKIN_TASKS:
            return CommandResult(
                output="Usage: /checkin morning|lunch|afternoon|evening|bedtime"
            )
        return CommandResult(output=session.send_checkin(parts[1], now=timestamp))
    if command == "/due":
        if len(parts) != 2 or parts[1] != "now":
            return CommandResult(output="Usage: /due now")
        outputs = session.send_due_tasks(now=timestamp)
        return CommandResult(output="\n".join(outputs) if outputs else "No due tasks.")
    return CommandResult(output="Unknown command. Use /help to view available commands.")
