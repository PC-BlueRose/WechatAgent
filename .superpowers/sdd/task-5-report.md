# Task 5 Report: LLM Gateway Interface and Deterministic Fake Gateway

## Implementation Summary

Implemented the Task 5 LLM abstraction layer in `src/wechat_agent/llm/gateway.py` and a deterministic fake implementation in `src/wechat_agent/llm/fake_gateway.py`.

Added:

- `ChatRequest`
- `ChatResponse`
- `ExtractedEvent`
- `ExtractionResult`
- `ImageAnalysisResult`
- `EmbeddingResult`
- `LLMGateway`
- `FakeLLMGateway.chat`
- `FakeLLMGateway.extract_life_events`
- `FakeLLMGateway.analyze_food_image`
- `FakeLLMGateway.embed`

Behavior matches the task brief exactly, including deterministic outputs for:

- morning check-in chat generation
- sleep extraction
- reminder extraction
- food image analysis
- embeddings based on text length

## Tests and Results

Command run:

```powershell
py -3.14 -m pytest tests/llm/test_fake_gateway.py -v
```

Results:

- initial RED run failed during collection with `ModuleNotFoundError: No module named 'wechat_agent.llm'`
- GREEN run passed all 3 tests

Passing tests:

- `test_fake_gateway_extracts_sleep_event_from_text`
- `test_fake_gateway_returns_uncertain_food_analysis`
- `test_fake_gateway_chat_uses_tone_and_intent`

## TDD RED/GREEN Evidence

### RED

After adding `tests/llm/test_fake_gateway.py`, running the targeted test command failed with:

```text
ModuleNotFoundError: No module named 'wechat_agent.llm'
```

This matched the task brief expectation.

### GREEN

After adding `src/wechat_agent/llm/gateway.py` and `src/wechat_agent/llm/fake_gateway.py`, rerunning the same command produced:

```text
3 passed
```

## Files Changed

- `src/wechat_agent/llm/gateway.py`
- `src/wechat_agent/llm/fake_gateway.py`
- `tests/llm/test_fake_gateway.py`

## Self-Review Findings

- Kept scope limited to interface models and deterministic fake behavior only.
- Did not add provider-specific networking, SDK wiring, or service orchestration.
- Reused existing package naming and Pydantic model style from earlier tasks.
- Preserved deterministic outputs so later memory, scheduler, and orchestrator tests can depend on exact values.
- No unrelated files were modified for implementation.

## Concerns

No implementation concerns for Task 5 itself.

The repository already contains unrelated local changes and untracked task artifacts outside Task 5 ownership. They were left untouched.

## Review Fixes

Addressed two Important review findings in one pass.

### Fix 1: Deterministic tone-aware chat behavior

Updated `FakeLLMGateway.chat` so responses now depend on both:

- `request.intent`
- `request.tone`

The fake remains deterministic and provider-free. It now supports distinct tone variants for the values later tasks are expected to pass:

- `gentle`
- `warm_daily`
- `encouraging`

This gives later mode-driven tasks a stable way to express quiet, daily, and coach semantics through tone without changing the gateway boundary.

### Fix 2: Stronger deterministic contract tests

Expanded `tests/llm/test_fake_gateway.py` to pin behavior for later tasks by adding:

- a tone-variation chat test for the same intent
- a reminder extraction test with exact payload and confidence assertions
- an embedding determinism test covering both normal-length and clamped long input

## Review Fix Tests and Results

Command run:

```powershell
py -3.14 -m pytest tests/llm/test_fake_gateway.py -v
```

RED/GREEN evidence for the review fixes:

- RED: after strengthening tests, `test_fake_gateway_chat_varies_by_tone_for_same_intent` failed because `chat()` ignored `request.tone`
- GREEN: after the tone-aware deterministic update, all 6 tests passed

Passing tests after fixes:

- `test_fake_gateway_extracts_sleep_event_from_text`
- `test_fake_gateway_returns_uncertain_food_analysis`
- `test_fake_gateway_chat_uses_tone_and_intent`
- `test_fake_gateway_chat_varies_by_tone_for_same_intent`
- `test_fake_gateway_extracts_reminder_event_from_text`
- `test_fake_gateway_embed_is_deterministic`
