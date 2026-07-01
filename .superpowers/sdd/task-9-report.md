# Task 9 Report

## Summary

Implemented the Task 9 vertical slice by adding a thin channel abstraction, a deterministic test channel adapter, a minimal in-memory metrics helper, README usage for the test channel MVP, and focused channel plus end-to-end tests.

Base commit context: `9fd3372d7172b619d0150f4f137f4bd4a0cf94ab`

## Files Changed

- `src/wechat_agent/channels/base.py`
- `src/wechat_agent/channels/test_channel.py`
- `src/wechat_agent/observability/metrics.py`
- `readme.md`
- `tests/channels/test_test_channel.py`
- `tests/e2e/test_personal_life_agent_flow.py`

## RED Evidence

Command:

```bash
py -3.14 -m pytest tests/channels/test_test_channel.py tests/e2e/test_personal_life_agent_flow.py -v
```

Result:

- Failed during collection.
- `ModuleNotFoundError: No module named 'wechat_agent.channels'`
- This matched the brief's expected missing channel-layer failure before implementation.

## GREEN Evidence

Command:

```bash
py -3.14 -m pytest tests/channels/test_test_channel.py tests/e2e/test_personal_life_agent_flow.py -v
```

Result:

- Passed.
- `2 passed in 0.13s`

Validated behaviors:

- `TestChannelAdapter.receive_text()` normalizes inbound text, routes it through `AgentOrchestrator`, stores the extracted sleep event, and records the reply in `sent_messages`.
- `TestChannelAdapter.receive_image()` routes inbound image messages through the image flow and stores the meal event.
- The end-to-end flow covers scheduled morning outreach plus inbound sleep and food-photo interactions with three outbound messages total.

## Full Suite

Command:

```bash
py -3.14 -m pytest -v
```

Result:

- Did not complete because of a pre-existing repository test collection issue outside the Task 9 file set.
- Error:
  - `import file mismatch`
  - Imported module `test_service` resolved to `tests/memory/test_service.py`
  - Pytest then failed when collecting `tests/scheduler/test_service.py`

This issue appears to come from duplicate existing test module basenames in non-package test directories and was not changed by Task 9.

## Ruff

Command:

```bash
py -3.14 -m ruff check .
```

Result:

- Could not run because `ruff` is not installed in the Python 3.14 environment on this machine.
- Exact error: `No module named ruff`

Additional verification:

```bash
py -3.14 -m pip show ruff
```

- Reported `Package(s) not found: ruff`

## Implementation Notes

- `ChannelAdapter` remains channel-specific and thin, with only normalization and send plumbing in its interface.
- `TestChannelAdapter` owns no memory, scheduling, or policy logic; it only builds normalized inbound messages, delegates to `AgentOrchestrator`, and captures outbound messages.
- Added `__test__ = False` to `TestChannelAdapter` so pytest does not try to collect it as a test class.
- `Metrics` stays minimal and in-memory, implemented as a simple counter wrapper.
- Updated the tracked lowercase `readme.md`, not a new uppercase README file.

## Self-Review

- Scope stayed within the Task 9 owned files plus the required appended report.
- The adapter behavior matches the approved brief and existing orchestration flow.
- Focused tests cover the new vertical slice directly.
- No unrelated refactors or reversions were made.
- Remaining concerns are limited to repo-wide validation blockers:
  - full-suite pytest collection conflict in existing tests
  - missing `ruff` installation for Python 3.14

## Fix Round: Full-Suite Blocker

Applied the smallest reasonable fix for the pytest collection conflict by adding package markers:

- `tests/__init__.py`
- `tests/memory/__init__.py`
- `tests/scheduler/__init__.py`

This changed pytest import resolution from ambiguous top-level `test_service` modules to package-qualified imports.

### Full Suite Re-Run

Command:

```bash
py -3.14 -m pytest -v
```

Output:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\BlueRose\AppData\Local\Python\pythoncore-3.14-64\python.exe
cachedir: .pytest_cache
rootdir: E:\Code\WechatAgent
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.0
collecting ... collected 34 items

tests/agent/test_orchestrator.py::test_text_message_is_saved_and_sleep_event_is_extracted PASSED [  2%]
tests/agent/test_orchestrator.py::test_reminder_message_schedules_user_reminder_task PASSED [  5%]
tests/agent/test_orchestrator.py::test_image_message_creates_estimated_meal_event PASSED [  8%]
tests/agent/test_orchestrator.py::test_scheduled_morning_checkin_generates_natural_message PASSED [ 11%]
tests/agent/test_orchestrator.py::test_quiet_mode_suppresses_routine_scheduled_checkin PASSED [ 14%]
tests/channels/test_test_channel.py::test_test_channel_receives_text_and_sends_reply PASSED [ 17%]
tests/domain/test_life_domain.py::test_life_event_carries_payload_confidence_and_estimate_flag PASSED [ 20%]
tests/domain/test_life_domain.py::test_long_term_memory_can_be_deprecated PASSED [ 23%]
tests/domain/test_life_domain.py::test_mode_config_can_expire PASSED     [ 26%]
tests/domain/test_life_domain.py::test_scheduled_task_tracks_status_and_intent PASSED [ 29%]
tests/domain/test_messages.py::test_normalized_text_message_has_required_channel_fields PASSED [ 32%]
tests/domain/test_messages.py::test_outgoing_message_targets_a_conversation PASSED [ 35%]
tests/e2e/test_personal_life_agent_flow.py::test_e2e_daily_checkin_sleep_reply_and_food_photo_flow PASSED [ 38%]
tests/llm/test_fake_gateway.py::test_fake_gateway_extracts_sleep_event_from_text PASSED [ 41%]
tests/llm/test_fake_gateway.py::test_fake_gateway_returns_uncertain_food_analysis PASSED [ 44%]
tests/llm/test_fake_gateway.py::test_fake_gateway_chat_uses_tone_and_intent PASSED [ 47%]
tests/llm/test_fake_gateway.py::test_fake_gateway_chat_varies_by_tone_for_same_intent PASSED [ 50%]
tests/llm/test_fake_gateway.py::test_fake_gateway_extracts_reminder_event_from_text PASSED [ 52%]
tests/llm/test_fake_gateway.py::test_fake_gateway_embed_is_deterministic PASSED [ 55%]
tests/memory/test_service.py::test_memory_service_saves_raw_message_before_extracted_event PASSED [ 58%]
tests/memory/test_service.py::test_memory_service_remembers_candidate_with_embedding PASSED [ 61%]
tests/memory/test_service.py::test_memory_service_recalls_active_memories_using_embedding_similarity PASSED [ 64%]
tests/memory/test_service.py::test_forget_memory_marks_memory_denied PASSED [ 67%]
tests/memory/test_service.py::test_memory_service_forget_works_without_prior_owner_caching PASSED [ 70%]
tests/memory/test_service.py::test_memory_service_forget_preserves_other_active_memories PASSED [ 73%]
tests/memory/test_service.py::test_memory_service_recall_raises_on_embedding_dimension_mismatch PASSED [ 76%]
tests/policy/test_engine.py::test_expired_quiet_mode_falls_back_to_daily PASSED [ 79%]
tests/policy/test_engine.py::test_quiet_mode_blocks_lunch_checkin_but_allows_user_reminder PASSED [ 82%]
tests/scheduler/test_service.py::test_scheduler_creates_five_daily_checkins PASSED [ 85%]
tests/scheduler/test_service.py::test_due_allowed_tasks_returns_pending_daily_task PASSED [ 88%]
tests/scheduler/test_service.py::test_create_user_reminder_preserves_required_fields PASSED [ 91%]
tests/storage/test_in_memory.py::test_in_memory_store_saves_raw_messages_before_events PASSED [ 94%]
tests/storage/test_in_memory.py::test_in_memory_store_lists_due_tasks_using_datetime_comparison PASSED [ 97%]
tests/storage/test_in_memory.py::test_in_memory_store_gets_memory_by_memory_id PASSED [100%]

============================= 34 passed in 0.15s ==============================
```

### Focused Task 9 Re-Run

Command:

```bash
py -3.14 -m pytest tests/channels/test_test_channel.py tests/e2e/test_personal_life_agent_flow.py -v
```

Output:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\BlueRose\AppData\Local\Python\pythoncore-3.14-64\python.exe
cachedir: .pytest_cache
rootdir: E:\Code\WechatAgent
configfile: pyproject.toml
plugins: anyio-4.14.0
collecting ... collected 2 items

tests/channels/test_test_channel.py::test_test_channel_receives_text_and_sends_reply PASSED [ 50%]
tests/e2e/test_personal_life_agent_flow.py::test_e2e_daily_checkin_sleep_reply_and_food_photo_flow PASSED [100%]

============================== 2 passed in 0.12s ==============================
```

### Ruff Note

No additional time was spent on `ruff` installation. The earlier environment finding still stands:

- `py -3.14 -m ruff check .` could not run because `ruff` is not installed for Python 3.14 on this machine.

## Fix Round: Raw Payload Preservation and Channel Contract Tests

Addressed the review findings by preserving the actual inbound raw payload in `TestChannelAdapter.normalize()` and strengthening the Task 9 tests around the normalization contract.

### Changes

- `src/wechat_agent/channels/test_channel.py`
  - Changed normalized metadata from a placeholder tag to the actual raw inbound payload: `metadata={"raw": dict(raw)}`
- `tests/channels/test_test_channel.py`
  - Added a direct normalization-contract test covering:
    - `channel == "test"`
    - `direction is MessageDirection.INBOUND`
    - `message_type is MessageType.TEXT`
    - preserved raw metadata equality
  - Strengthened the receive-text test to assert the stored inbound message preserves channel, direction, message type, and raw metadata fields.
- `tests/e2e/test_personal_life_agent_flow.py`
  - Added a light end-to-end assertion that the stored inbound image message preserves raw metadata for image flow.

### Focused Task 9 Re-Run

Command:

```bash
py -3.14 -m pytest tests/channels/test_test_channel.py tests/e2e/test_personal_life_agent_flow.py -v
```

Output summary:

- Passed.
- `3 passed in 0.14s`

### Full Suite Re-Run

Command:

```bash
py -3.14 -m pytest -v
```

Output summary:

- Passed.
- `35 passed in 0.16s`
