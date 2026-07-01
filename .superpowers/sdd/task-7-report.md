# Task 7 Report: Scheduler Service for Check-In Windows and Reminders

## Implementation Summary

Implemented `SchedulerService` in `src/wechat_agent/scheduler/service.py` with the required behavior:

- `create_daily_checkins(...)` creates and stores five routine check-in tasks for a given day using the exact task types, UTC trigger times, and payload goals from the task brief.
- `create_user_reminder(...)` creates and stores a pending `USER_REMINDER` task with reminder content and optional source message linkage.
- `due_allowed_tasks(...)` reads due pending tasks from `InMemoryStore`, evaluates each through `PolicyEngine.evaluate_checkin(...)`, and returns only allowed tasks.

Added targeted tests in `tests/scheduler/test_service.py` for:

- creation order of the five daily check-ins
- retrieval of a due pending morning task once its trigger window has passed

## Tests and Results

Command run:

```powershell
py -3.14 -m pytest tests\scheduler\test_service.py -v
```

Result:

- `2 passed in 0.16s`

## TDD RED/GREEN Evidence

### RED

After adding the tests and before implementing the scheduler service, running:

```powershell
py -3.14 -m pytest tests\scheduler\test_service.py -v
```

failed during collection with:

- `ModuleNotFoundError: No module named 'wechat_agent.scheduler'`

This matched the task brief's expected failing state.

### GREEN

After implementing `src/wechat_agent/scheduler/service.py`, rerunning the same command passed:

- `tests/scheduler/test_service.py::test_scheduler_creates_five_daily_checkins PASSED`
- `tests/scheduler/test_service.py::test_due_allowed_tasks_returns_pending_daily_task PASSED`

## Files Changed

- `src/wechat_agent/scheduler/service.py`
- `tests/scheduler/test_service.py`
- `.superpowers/sdd/task-7-report.md`

## Self-Review Findings

- Reused `PolicyEngine`, `InMemoryStore`, `ScheduledTask`, `TaskType`, and `TaskStatus` without changing existing abstractions.
- Kept scope limited to scheduler behavior only; no orchestrator or channel dispatch logic added.
- Preserved task storage and policy filtering behavior through existing repository and engine interfaces.
- Did not revert or modify unrelated user changes in the worktree.

## Concerns

- The task brief limited tests to two scheduler cases, so `create_user_reminder(...)` is implemented but not directly covered by this task's targeted test file.

## Review Fix Follow-Up

Addressed review feedback that `create_user_reminder(...)` was part of the required public interface but untested.

Added `test_create_user_reminder_preserves_required_fields` to `tests/scheduler/test_service.py` to verify that reminder creation:

- stores a task with `TaskStatus.PENDING`
- uses `TaskType.USER_REMINDER`
- preserves `trigger_at`
- preserves `payload["content"]`
- preserves `source_message_id`

### Follow-Up Test Results

Command run:

```powershell
py -3.14 -m pytest tests\scheduler\test_service.py -v
```

Result:

- `3 passed in 0.17s`

### Updated Self-Review

- The scheduler public interface now has direct targeted coverage for both daily check-ins and user reminder creation.
- Scope remained limited to Task 7 owned files plus the task report.
