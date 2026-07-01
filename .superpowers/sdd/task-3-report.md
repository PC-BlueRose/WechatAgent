# Task 3 Report

## Implementation Summary

Implemented Task 3 exactly to brief by adding:
- repository `Protocol` definitions in `src/wechat_agent/storage/repositories.py`
- in-memory repository implementations plus `InMemoryStore` composition in `src/wechat_agent/storage/in_memory.py`
- PostgreSQL/pgvector target schema in `src/wechat_agent/storage/schema.sql`
- the required storage regression test in `tests/storage/test_in_memory.py`

The implementation matches the Task 1-2 domain model types directly and keeps behavior scoped to storage concerns only.

## Tests and Results

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: `1 passed`

## TDD RED/GREEN Evidence

### RED

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: failed during collection with `ModuleNotFoundError: No module named 'wechat_agent.storage'`

### GREEN

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: `tests/storage/test_in_memory.py::test_in_memory_store_saves_raw_messages_before_events PASSED`

## Files Changed

- `src/wechat_agent/storage/repositories.py`
- `src/wechat_agent/storage/in_memory.py`
- `src/wechat_agent/storage/schema.sql`
- `tests/storage/test_in_memory.py`

## Self-Review Findings

- Protocol names and method signatures match the task brief verbatim, including `TaskRepository.list_due(self, user_id: str, now_iso: str) -> list[ScheduledTask]`.
- In-memory repositories are intentionally thin and do not introduce service logic or extra validation beyond the domain models and brief.
- The schema uses the exact table/column defaults and `vector(1536)` definition specified in the brief.
- The owned test proves the intended ordering dependency: raw messages can be saved and then referenced by saved life events.

## Concerns

- None for Task 3 scope.

## Follow-up Fix: Due Task Datetime Comparison

Addressed review feedback in `InMemoryTaskRepository.list_due(self, user_id: str, now_iso: str)` without changing the public signature from the brief.

### Fix Summary

- Parsed `now_iso` with `datetime.fromisoformat(now_iso)` inside `list_due()`
- Compared `task.trigger_at <= now` as datetimes rather than comparing ISO-formatted strings lexicographically
- Added a focused regression test covering timezone-offset input where string ordering and real datetime ordering diverge

### Follow-up TDD Evidence

#### RED

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: `test_in_memory_store_lists_due_tasks_using_datetime_comparison` failed because the string-based comparison incorrectly returned a pending task as due for `2026-07-01T10:00:00+01:00`

#### GREEN

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: `2 passed`

### Follow-up Files Changed

- `src/wechat_agent/storage/in_memory.py`
- `tests/storage/test_in_memory.py`

## Follow-up Fix: Memory Repository Lookup by `memory_id`

Applied the approved Task 3 amendment so memory repositories can look up a memory directly by `memory_id`, which unblocks later forgetting flows without private backend access.

### Implementation Summary

- Added `MemoryRepository.get(memory_id: str) -> LongTermMemory | None` to the storage repository protocol in `src/wechat_agent/storage/repositories.py`
- Implemented `InMemoryMemoryRepository.get()` in `src/wechat_agent/storage/in_memory.py`
- Added a focused storage test that proves saved memories can be retrieved by `memory_id` and that unknown IDs return `None`

### Tests and Results

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: `3 passed`

### TDD RED/GREEN Evidence

#### RED

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: `test_in_memory_store_gets_memory_by_memory_id` failed with `AttributeError: 'InMemoryMemoryRepository' object has no attribute 'get'`

#### GREEN

- Command: `py -3.14 -m pytest tests\storage\test_in_memory.py -v`
- Result: all storage tests passed, including `test_in_memory_store_gets_memory_by_memory_id`

### Files Changed

- `src/wechat_agent/storage/repositories.py`
- `src/wechat_agent/storage/in_memory.py`
- `tests/storage/test_in_memory.py`
- `.superpowers/sdd/task-3-report.md`

### Concerns

- None for Task 3 scope.
