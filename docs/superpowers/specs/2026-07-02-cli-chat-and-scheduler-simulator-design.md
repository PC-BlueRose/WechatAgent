# CLI Chat And Scheduler Simulator Design

## Goal

Add a first runnable command-line interface for the current WechatAgent MVP so a human can:

- chat with the Agent in a persistent terminal session
- switch Agent modes on demand
- simulate proactive daily check-ins
- simulate due-task delivery for reminders and scheduled prompts
- inspect the in-memory state at a summary level

This CLI is a thin testing shell over the existing core. It is not a second product surface and it is not a production operator console.

## Scope

### In Scope

- one single-process interactive CLI session
- plain-text chat input
- slash commands for mode switching, scheduled check-in simulation, due-task delivery, state inspection, help, and exit
- reuse of the existing `InMemoryStore`, `FakeLLMGateway`, `PolicyEngine`, `MemoryService`, `SchedulerService`, `AgentOrchestrator`, and `TestChannelAdapter`
- tests for command parsing and core CLI flows
- README usage instructions for the CLI

### Out Of Scope

- real WeChat integration
- web UI
- image upload from the terminal
- background polling or multi-process scheduling
- persistent storage beyond the current in-memory runtime
- log files, retries, or advanced operator tooling

## Recommended Approach

Use a single-process interactive CLI that owns one in-memory session and treats normal text as inbound user messages while reserving slash commands for simulation and debugging.

This is preferred over a split-command CLI or a background-loop CLI because it keeps the test experience fast, preserves the current channel-independent core, and avoids premature runtime complexity.

## User Experience

After startup, the CLI opens a continuous REPL-style session.

Normal input:

```text
> I slept around 2 and woke up tired.
Agent: I am here. Take your time.
```

Slash commands:

```text
/help
/mode quiet
/mode daily
/mode coach
/checkin morning
/checkin lunch
/checkin afternoon
/checkin evening
/checkin bedtime
/due now
/state
/exit
```

### Input Rules

- any line not starting with `/` is treated as a user text message
- the first version supports text only
- commands are case-sensitive and use lowercase keywords
- unknown commands return a short error plus a `/help` hint

### Output Rules

- Agent replies are printed as `Agent: <content>`
- command confirmations are printed as concise status lines
- command failures do not terminate the session
- `/state` prints a compact summary rather than raw model dumps

## Command Semantics

### `/help`

Print the supported commands with one-line descriptions and a few examples.

### `/mode quiet|daily|coach`

Update the active `ModeConfig` for the session user and confirm the selected mode.

The CLI will write a fresh mode config into the existing mode repository using the current wall-clock time. The first version does not expose time-limited mode expiration controls through the CLI.

### `/checkin morning|lunch|afternoon|evening|bedtime`

Create and immediately send one corresponding proactive check-in message through the existing orchestration path.

This command is intentionally for fast manual simulation. It does not need to wait for the task to become due.

The mapping is:

- `morning` -> `TaskType.MORNING_CHECKIN`
- `lunch` -> `TaskType.LUNCH_MEAL_CHECKIN`
- `afternoon` -> `TaskType.AFTERNOON_ENERGY_CHECKIN`
- `evening` -> `TaskType.EVENING_REVIEW`
- `bedtime` -> `TaskType.BEDTIME_WINDDOWN`

### `/due now`

Ask `SchedulerService` for due allowed tasks at the current time and deliver each one through `AgentOrchestrator.handle_scheduled_task(...)`.

If no tasks are due, print a short message such as `No due tasks.`.

### `/state`

Print a compact debug summary containing:

- current mode
- most recent five life events with event type and timestamp
- active memory count
- task counts grouped by status

This command is read-only and must not expose raw internal object repr output.

### `/exit`

Exit the CLI session cleanly.

## Architecture

### Module Layout

- `src/wechat_agent/cli/session.py`
  - builds one in-memory runtime session
  - owns shared user identity, conversation identity, and channel identity for the CLI run
  - wires together store, fake LLM, policy, memory, scheduler, orchestrator, and test channel

- `src/wechat_agent/cli/commands.py`
  - parses slash commands
  - validates command arguments
  - dispatches command handlers against the session object
  - returns structured results for the app layer to print

- `src/wechat_agent/cli/app.py`
  - runs the interactive read-eval-print loop
  - routes normal text to the test channel
  - routes slash commands through the command layer
  - handles friendly errors and session exit

The CLI package is an adapter layer only. It must not move business decisions out of existing core modules.

### Session Model

One CLI process creates one session with:

- a fixed `user_id`, such as `cli-user`
- a fixed `conversation_id`, such as `cli-conversation`
- channel name `test`

This keeps the runtime deterministic and avoids introducing account management concerns into the MVP.

### Data Flow

### Plain Text Message

1. user enters normal text
2. CLI builds an inbound text message via `TestChannelAdapter`
3. `AgentOrchestrator.handle_message(...)` processes it
4. CLI prints the returned Agent reply

### Immediate Check-In Simulation

1. user enters `/checkin <kind>`
2. command layer maps kind to `TaskType`
3. session creates a scheduled task for the current time
4. orchestrator handles that scheduled task immediately
5. CLI prints the proactive Agent message

### Due Task Delivery

1. user enters `/due now`
2. session asks scheduler for due allowed tasks at current time
3. CLI delivers each due task through the orchestrator
4. CLI prints each outbound message

### Mode Switch

1. user enters `/mode <name>`
2. session writes a new mode config into the store
3. subsequent inbound and scheduled replies reflect the chosen tone and policy behavior

## Error Handling

- invalid command: print `Unknown command` plus `/help`
- invalid command argument: print a short usage hint for that command
- Agent processing error: print `Agent error: <message>` and continue
- no due tasks: print a neutral no-op message
- no events or memories yet in `/state`: print zero-count summaries, not errors

The CLI should stay alive after any recoverable command failure.

## Testing Strategy

Add focused tests for:

- command parsing and validation
- plain-text chat flow through the CLI session
- mode switching behavior
- immediate check-in simulation
- due-task delivery path
- `/state` summary formatting at a minimal level

Keep tests at the CLI boundary thin and behavior-oriented. Core business logic remains covered by existing orchestrator, scheduler, policy, and LLM tests.

## README Changes

Update the README to document:

- how to start the CLI
- supported commands
- the fact that this is a local test harness over the in-memory MVP

## Success Criteria

The design is successful when:

- a user can start one command and chat with the Agent in a terminal
- the user can switch between quiet, daily, and coach mode and observe different reply tone
- the user can trigger daily check-in simulations without waiting on real scheduling
- the user can create reminders through normal chat and later deliver them through `/due now`
- the user can inspect session state without reading Python internals

## Constraints And Non-Goals

- preserve the existing modular Python monolith boundaries
- keep the Agent core channel-independent
- avoid adding persistence or background runtime complexity
- do not add image input for the first CLI iteration
- do not bypass existing orchestration and policy layers for convenience
