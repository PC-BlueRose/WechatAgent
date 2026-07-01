# Task 6 Report

## Implementation Summary

Implemented `MemoryService` in `src/wechat_agent/memory/service.py` as a thin behavior layer over the existing `InMemoryStore` and `LLMGateway` boundaries.

- `save_raw_message(message)` persists the normalized message directly to `store.messages`.
- `extract_and_store(message)` saves the raw message before any extraction logic, skips non-text or empty-content messages, calls `llm.extract_life_events(...)`, maps extracted events into `LifeEvent` models, and saves them to `store.life_events`.
- `remember_candidate(user_id, category, content, source_ref)` creates an `ACTIVE` `LongTermMemory`, uses `llm.embed(content)` for its embedding, and saves it through `store.memories`.
- `recall(user_id, query, limit)` embeds the query, ranks active memories deterministically by absolute embedding distance, and returns up to `limit` memories.
- `forget_memory(memory_id)` leaves repository structure unchanged and marks the targeted memory as `DENIED` through `store.memories.replace(...)`.

## Tests and Results

Targeted test command:

```powershell
py -3.14 -m pytest tests\memory\test_service.py -v
```

Final result:

- `4 passed in 0.14s`

Covered behaviors:

- raw message is saved before extracted event persistence
- remembered memory candidate is stored as active with fake-gateway embedding
- recall returns active memories ranked by deterministic embedding similarity
- forgetting a memory removes it from active recall by marking it denied

## TDD RED/GREEN Evidence

RED run in a temporary snapshot exported from base commit `2431e74` with the new Task 6 test file copied in:

```powershell
$tempRoot = Join-Path $env:TEMP 'wechatagent-task6-red'
git archive 2431e74 -o (Join-Path $env:TEMP 'wechatagent-task6-red.tar')
tar -xf (Join-Path $env:TEMP 'wechatagent-task6-red.tar') -C $tempRoot
Copy-Item tests\memory\test_service.py (Join-Path $tempRoot 'tests\memory\test_service.py')
Push-Location $tempRoot
py -3.14 -m pytest tests\memory\test_service.py -v
Pop-Location
```

Observed failure:

- test collection failed before execution because Task 6 had not been implemented yet in that snapshot
- `ModuleNotFoundError: No module named 'wechat_agent.memory'`

GREEN run in the current workspace after implementing Task 6:

```powershell
py -3.14 -m pytest tests\memory\test_service.py -v
```

Observed result:

- `4 passed in 0.14s`

## Commit Information

- Commit message: `feat: add memory service`

## Files Changed

- `src/wechat_agent/memory/service.py`
- `tests/memory/test_service.py`

## Self-Review Findings

- Stayed within the owned Task 6 files only.
- Preserved the existing `InMemoryStore` and `LLMGateway` interfaces without redesigning repositories.
- Ensured raw-message persistence happens before any extraction work.
- Kept recall deterministic and narrow in scope, using the existing fake embedding behavior rather than inventing semantic matching machinery.
- `forget_memory` is tolerant of unknown memory IDs and performs an in-place repository replacement for known IDs.

## Concerns

- `forget_memory` reads the backing in-memory repository dictionary to locate a memory by ID because the current repository API does not expose a `get(...)` method. This stays within the existing boundary constraints for Task 6, but a future repository abstraction may want an explicit lookup method.
