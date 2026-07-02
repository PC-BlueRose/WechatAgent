## Task 2: Interactive CLI App And Entry Point

### Scope

- Implemented `src/wechat_agent/cli/app.py`
- Updated `pyproject.toml`
- Added `tests/cli/test_app.py`

### RED

Command:

```powershell
py -3.14 -m pytest tests/cli/test_app.py -v
```

Result:

```text
collected 0 items / 1 error
ModuleNotFoundError: No module named 'wechat_agent.cli.app'
```

### Implementation

Files changed:

- `src/wechat_agent/cli/app.py`
- `pyproject.toml`
- `tests/cli/test_app.py`

What changed:

- Added `run_cli_once(session, user_input, now=None)` to route slash commands through `run_command(...)` and plain text through `CliSession.handle_text(...)`
- Added `main()` REPL loop with startup banner, blank-line skip behavior, friendly `EOFError`/`KeyboardInterrupt` exits, and an interactive exception safety net
- Added `[project.scripts]` entry for `wechat-agent-cli`
- Added focused tests for plain text routing, slash command routing, and `/exit`

### GREEN

Command:

```powershell
py -3.14 -m pytest tests/cli/test_app.py -v
```

Result:

```text
collected 3 items
tests/cli/test_app.py::test_run_cli_once_routes_plain_text_to_agent_reply PASSED
tests/cli/test_app.py::test_run_cli_once_routes_slash_command_through_command_engine PASSED
tests/cli/test_app.py::test_run_cli_once_marks_exit_command PASSED
3 passed in 0.14s
```

### Self-review

- Kept the CLI adapter thin and reused Task 1’s `build_cli_session()` and `run_command(...)` exactly as required
- Limited ownership to the requested files only
- Did not add extra behavior beyond the brief; interactive safety handling is confined to `main()` and excluded from test coverage as an intentional REPL guard
- Did not commit in this task
## Fix Round After Review

### Findings addressed

1. `run_cli_once()` now strips leading and trailing whitespace before deciding whether input is a slash command.
2. `tests/cli/test_app.py` now covers representative `main()` REPL behavior in addition to helper routing.

### Changes

- Updated `src/wechat_agent/cli/app.py` to normalize `user_input` once inside `run_cli_once()`
- Added a regression test for whitespace-padded slash commands
- Added a `main()` test for startup banner plus EOF exit
- Added a `main()` test for blank-line skip behavior and `Agent: ` prefixing of plain-text replies

### Verification

Command:

```powershell
py -3.14 -m pytest tests/cli/test_app.py -v
```

Result:

```text
collected 6 items
tests/cli/test_app.py::test_run_cli_once_routes_plain_text_to_agent_reply PASSED
tests/cli/test_app.py::test_run_cli_once_routes_slash_command_through_command_engine PASSED
tests/cli/test_app.py::test_run_cli_once_marks_exit_command PASSED
tests/cli/test_app.py::test_run_cli_once_normalizes_whitespace_before_command_routing PASSED
tests/cli/test_app.py::test_main_prints_startup_banner_and_exits_on_eof PASSED
tests/cli/test_app.py::test_main_skips_blank_lines_and_prefixes_agent_output PASSED
6 passed in 0.12s
```

### Self-review

- The CLI adapter remains thin; normalization stays inside `run_cli_once()` and `main()` behavior is unchanged except for the whitespace fix reaching helper callers too
- The new tests target user-visible REPL behavior without trying to exhaustively script every branch of the loop

## Final Fix Before Review

### Finding addressed

- `main()` now uses the same normalized command detection for output prefixing that `run_cli_once()` already uses for dispatch.

### Changes

- Updated `src/wechat_agent/cli/app.py` so `main()` strips once, skips blank input from the normalized value, passes normalized input into `run_cli_once()`, and decides the `Agent: ` prefix from that same normalized string
- Added a focused REPL regression test proving `"  /mode quiet  "` prints `Mode set to quiet.` without the `Agent: ` prefix

### Verification

Command:

```powershell
py -3.14 -m pytest tests/cli/test_app.py -v
```

Result:

```text
collected 7 items
tests/cli/test_app.py::test_run_cli_once_routes_plain_text_to_agent_reply PASSED
tests/cli/test_app.py::test_run_cli_once_routes_slash_command_through_command_engine PASSED
tests/cli/test_app.py::test_run_cli_once_marks_exit_command PASSED
tests/cli/test_app.py::test_run_cli_once_normalizes_whitespace_before_command_routing PASSED
tests/cli/test_app.py::test_main_prints_startup_banner_and_exits_on_eof PASSED
tests/cli/test_app.py::test_main_skips_blank_lines_and_prefixes_agent_output PASSED
tests/cli/test_app.py::test_main_does_not_prefix_whitespace_padded_slash_command_output PASSED
7 passed in 0.15s
```

### Self-review

- This keeps the CLI adapter thin and removes the last mismatch between command dispatch and command rendering in `main()`

## Post-final Fix Round

### Findings addressed

1. `pyproject.toml` now lands in the Task 2 commit set with the required `[project.scripts]` entry for `wechat-agent-cli`.
2. `run_cli_once()` still normalizes enough to detect whitespace-padded slash commands, but now preserves raw plain-text chat payloads when routing to `session.handle_text(...)`.

### Changes

- Kept `[project.scripts]` in `pyproject.toml` so `wechat-agent-cli = "wechat_agent.cli.app:main"` is part of the committed Task 2 changes
- Updated `src/wechat_agent/cli/app.py` so `run_cli_once()` dispatches commands from a stripped copy while passing original plain text through unchanged
- Updated `main()` to continue using normalized input only for blank-line detection and prefix selection, while passing the original user input into `run_cli_once()`
- Added a focused regression test proving plain-text whitespace is preserved for the agent
- Kept the whitespace-padded slash-command regression coverage

### Verification

Command:

```powershell
py -3.14 -m pytest tests/cli/test_app.py -v
```

Result:

```text
collected 8 items
tests/cli/test_app.py::test_run_cli_once_routes_plain_text_to_agent_reply PASSED
tests/cli/test_app.py::test_run_cli_once_preserves_plain_text_whitespace_for_agent PASSED
tests/cli/test_app.py::test_run_cli_once_routes_slash_command_through_command_engine PASSED
tests/cli/test_app.py::test_run_cli_once_marks_exit_command PASSED
tests/cli/test_app.py::test_run_cli_once_normalizes_whitespace_before_command_routing PASSED
tests/cli/test_app.py::test_main_prints_startup_banner_and_exits_on_eof PASSED
tests/cli/test_app.py::test_main_skips_blank_lines_and_prefixes_agent_output PASSED
tests/cli/test_app.py::test_main_does_not_prefix_whitespace_padded_slash_command_output PASSED
8 passed in 0.13s
```

### Self-review

- The CLI stays thin: normalization is only used where the REPL needs it for blank lines and command detection
- Plain-text payload preservation is now explicit and regression-tested
