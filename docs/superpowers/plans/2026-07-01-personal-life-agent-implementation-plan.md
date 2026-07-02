# Personal Life Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable modular Python monolith for a channel-independent personal life Agent with normalized messages, memory, scheduling, modes, LLM gateway abstraction, and a test channel.

**Architecture:** Implement a small FastAPI-free core first: pure Python modules with explicit interfaces and in-memory repositories, then add PostgreSQL-ready boundaries after behavior is covered by tests. The first working system runs through a CLI/test channel while keeping WeChat, model vendors, and persistent storage behind replaceable adapters.

**Tech Stack:** Python 3.12.10 baseline, PostgreSQL 16 target, pytest, pydantic v2, SQLAlchemy 2.0, Alembic, psycopg, pgvector-ready schema, ruff.

## Global Constraints

- Use a modular Python monolith.
- Python 3.12.10 baseline.
- PostgreSQL 16 target.
- Agent Core must be channel-independent and process normalized messages, not WeChat-specific payloads.
- First version can use a CLI, webhook, or simple test channel; direct personal WeChat integration is not required.
- Database target is PostgreSQL with pgvector.
- Remote model APIs must be wrapped behind an LLM Gateway interface.
- The Agent must support quiet, daily, and coach modes, including time-limited mode changes.
- Health and nutrition analysis must be framed as lifestyle support and estimates, not diagnosis.
- Outbound messages to third parties are out of scope for the first version.
- Store raw input before analysis so extraction can be reprocessed.
- Use TDD for each task and commit after each independently testable deliverable.

---

## File Structure

Create this structure:

```text
pyproject.toml
README.md
src/wechat_agent/__init__.py
src/wechat_agent/domain/messages.py
src/wechat_agent/domain/events.py
src/wechat_agent/domain/memory.py
src/wechat_agent/domain/modes.py
src/wechat_agent/domain/tasks.py
src/wechat_agent/channels/base.py
src/wechat_agent/channels/test_channel.py
src/wechat_agent/agent/orchestrator.py
src/wechat_agent/llm/gateway.py
src/wechat_agent/llm/fake_gateway.py
src/wechat_agent/memory/service.py
src/wechat_agent/policy/engine.py
src/wechat_agent/scheduler/service.py
src/wechat_agent/storage/repositories.py
src/wechat_agent/storage/in_memory.py
src/wechat_agent/storage/schema.sql
src/wechat_agent/observability/metrics.py
tests/domain/test_messages.py
tests/policy/test_engine.py
tests/llm/test_fake_gateway.py
tests/memory/test_service.py
tests/scheduler/test_service.py
tests/agent/test_orchestrator.py
tests/channels/test_test_channel.py
tests/e2e/test_personal_life_agent_flow.py
```

Responsibilities:

- `domain/*`: Pydantic models and enums shared across modules. No I/O.
- `channels/*`: Normalize platform input and send outgoing replies. No memory or Agent decisions.
- `agent/orchestrator.py`: Main decision flow for incoming messages and scheduled intents.
- `llm/*`: Model gateway interface and deterministic fake gateway for tests.
- `memory/service.py`: Raw message storage, structured event writes, long-term memory writes, recall.
- `policy/engine.py`: Modes, interruption checks, risk classification decisions.
- `scheduler/service.py`: Check-in and reminder task generation.
- `storage/*`: Repository protocols and in-memory implementations. SQL schema is PostgreSQL/pgvector-oriented.
- `observability/metrics.py`: In-memory counters for MVP behavior and tests.

---

### Task 1: Project Skeleton and Domain Message Model

**Files:**
- Create: `pyproject.toml`
- Create: `src/wechat_agent/__init__.py`
- Create: `src/wechat_agent/domain/messages.py`
- Test: `tests/domain/test_messages.py`

**Interfaces:**
- Produces: `MessageType`, `MessageDirection`, `NormalizedMessage`, `OutgoingMessage`.
- Later tasks consume `NormalizedMessage` and `OutgoingMessage`.

- [ ] **Step 1: Write the failing test**

Create `tests/domain/test_messages.py`:

```python
from datetime import UTC, datetime

from wechat_agent.domain.messages import (
    MessageDirection,
    MessageType,
    NormalizedMessage,
    OutgoingMessage,
)


def test_normalized_text_message_has_required_channel_fields():
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2 and woke up tired.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 30, tzinfo=UTC),
        metadata={"source": "unit-test"},
    )

    assert message.message_type is MessageType.TEXT
    assert message.direction is MessageDirection.INBOUND
    assert message.content == "I slept around 2 and woke up tired."
    assert message.metadata["source"] == "unit-test"


def test_outgoing_message_targets_a_conversation():
    outgoing = OutgoingMessage(
        conversation_id="conv-1",
        channel="test",
        content="Morning. How did you sleep last night?",
        metadata={"reason": "morning_checkin"},
    )

    assert outgoing.conversation_id == "conv-1"
    assert outgoing.channel == "test"
    assert outgoing.content.startswith("Morning")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_messages.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wechat_agent'`.

- [ ] **Step 3: Add project metadata and message models**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=70"]
build-backend = "setuptools.build_meta"

[project]
name = "wechat-agent"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.8,<3",
  "sqlalchemy>=2.0,<3",
  "psycopg[binary]>=3.2,<4",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9",
  "ruff>=0.5,<1",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

Create `src/wechat_agent/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `src/wechat_agent/domain/messages.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    SYSTEM = "system"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class NormalizedMessage(BaseModel):
    message_id: str
    user_id: str
    conversation_id: str
    channel: str
    direction: MessageDirection
    message_type: MessageType
    content: str | None = None
    media_ref: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutgoingMessage(BaseModel):
    conversation_id: str
    channel: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/domain/test_messages.py -v`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/wechat_agent/__init__.py src/wechat_agent/domain/messages.py tests/domain/test_messages.py
git commit -m "feat: add normalized message domain model"
```

---

### Task 2: Life Events, Memories, Modes, and Tasks Domain Models

**Files:**
- Create: `src/wechat_agent/domain/events.py`
- Create: `src/wechat_agent/domain/memory.py`
- Create: `src/wechat_agent/domain/modes.py`
- Create: `src/wechat_agent/domain/tasks.py`
- Test: `tests/domain/test_life_domain.py`

**Interfaces:**
- Consumes: no code from earlier tasks.
- Produces: `LifeEvent`, `LifeEventType`, `LongTermMemory`, `MemoryState`, `AgentMode`, `ModeConfig`, `ScheduledTask`, `TaskType`, `TaskStatus`.
- Later tasks use these exact names.

- [ ] **Step 1: Write the failing test**

Create `tests/domain/test_life_domain.py`:

```python
from datetime import UTC, datetime, timedelta

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType


def test_life_event_carries_payload_confidence_and_estimate_flag():
    event = LifeEvent(
        event_id="event-1",
        user_id="user-1",
        event_type=LifeEventType.SLEEP,
        occurred_at=datetime(2026, 7, 1, 2, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 7, 1, 8, 30, tzinfo=UTC),
        source_message_id="msg-1",
        confidence=0.84,
        payload={"sleep_time": "02:00", "waking_state": "tired"},
        is_estimate=True,
        confirmation_status="unconfirmed",
    )

    assert event.event_type is LifeEventType.SLEEP
    assert event.payload["waking_state"] == "tired"
    assert event.is_estimate is True


def test_long_term_memory_can_be_deprecated():
    memory = LongTermMemory(
        memory_id="mem-1",
        user_id="user-1",
        category="preference",
        content="User prefers gentle reminders.",
        importance=0.7,
        confidence=0.9,
        source_ref="msg-1",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
        updated_at=datetime(2026, 7, 1, tzinfo=UTC),
        state=MemoryState.DEPRECATED,
        embedding=None,
    )

    assert memory.state is MemoryState.DEPRECATED


def test_mode_config_can_expire():
    now = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    config = ModeConfig(
        user_id="user-1",
        mode=AgentMode.QUIET,
        started_at=now - timedelta(hours=2),
        expires_at=now - timedelta(minutes=1),
        do_not_disturb_windows=[],
        daily_checkin_windows={"morning": ["07:30", "10:30"]},
        tone_preferences={"default": "gentle"},
        memory_strategy="explicit_only",
    )

    assert config.is_expired(now) is True


def test_scheduled_task_tracks_status_and_intent():
    task = ScheduledTask(
        task_id="task-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        task_type=TaskType.MORNING_CHECKIN,
        status=TaskStatus.PENDING,
        trigger_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        payload={"goal": "collect_sleep_and_mood"},
        source_message_id=None,
    )

    assert task.task_type is TaskType.MORNING_CHECKIN
    assert task.payload["goal"] == "collect_sleep_and_mood"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_life_domain.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.domain.events`.

- [ ] **Step 3: Add domain models**

Create `src/wechat_agent/domain/events.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LifeEventType(StrEnum):
    SLEEP = "sleep"
    DREAM = "dream"
    MEAL = "meal"
    MOOD = "mood"
    ENERGY = "energy"
    BODY_STATUS = "body_status"
    PLAN = "plan"
    REMINDER = "reminder"
    EXERCISE = "exercise"
    DAILY_REVIEW = "daily_review"


class LifeEvent(BaseModel):
    event_id: str
    user_id: str
    event_type: LifeEventType
    occurred_at: datetime
    recorded_at: datetime
    source_message_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict)
    is_estimate: bool
    confirmation_status: str
```

Create `src/wechat_agent/domain/memory.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryState(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DEPRECATED = "deprecated"
    DENIED = "denied"


class LongTermMemory(BaseModel):
    memory_id: str
    user_id: str
    category: str
    content: str
    importance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    source_ref: str
    created_at: datetime
    updated_at: datetime
    state: MemoryState
    embedding: list[float] | None
```

Create `src/wechat_agent/domain/modes.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AgentMode(StrEnum):
    QUIET = "quiet"
    DAILY = "daily"
    COACH = "coach"


class ModeConfig(BaseModel):
    user_id: str
    mode: AgentMode
    started_at: datetime
    expires_at: datetime | None
    do_not_disturb_windows: list[tuple[str, str]] = Field(default_factory=list)
    daily_checkin_windows: dict[str, list[str]] = Field(default_factory=dict)
    tone_preferences: dict[str, str] = Field(default_factory=dict)
    memory_strategy: str

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at
```

Create `src/wechat_agent/domain/tasks.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(StrEnum):
    MORNING_CHECKIN = "morning_checkin"
    LUNCH_MEAL_CHECKIN = "lunch_meal_checkin"
    AFTERNOON_ENERGY_CHECKIN = "afternoon_energy_checkin"
    EVENING_REVIEW = "evening_review"
    BEDTIME_WINDDOWN = "bedtime_winddown"
    USER_REMINDER = "user_reminder"
    WEEKLY_SUMMARY = "weekly_summary"


class TaskStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DONE = "done"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class ScheduledTask(BaseModel):
    task_id: str
    user_id: str
    conversation_id: str
    channel: str
    task_type: TaskType
    status: TaskStatus
    trigger_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    source_message_id: str | None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/domain/test_life_domain.py -v`

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/domain/events.py src/wechat_agent/domain/memory.py src/wechat_agent/domain/modes.py src/wechat_agent/domain/tasks.py tests/domain/test_life_domain.py
git commit -m "feat: add life tracking domain models"
```

---

### Task 3: Repository Protocols, In-Memory Storage, and PostgreSQL Schema

**Files:**
- Create: `src/wechat_agent/storage/repositories.py`
- Create: `src/wechat_agent/storage/in_memory.py`
- Create: `src/wechat_agent/storage/schema.sql`
- Test: `tests/storage/test_in_memory.py`

**Interfaces:**
- Consumes: `NormalizedMessage`, `LifeEvent`, `LongTermMemory`, `ModeConfig`, `ScheduledTask`.
- Produces: `MessageRepository`, `LifeEventRepository`, `MemoryRepository`, `ModeRepository`, `TaskRepository`, `InMemoryStore`.
- Later tasks consume `InMemoryStore`.

- [ ] **Step 1: Write the failing test**

Create `tests/storage/test_in_memory.py`:

```python
from datetime import UTC, datetime

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.storage.in_memory import InMemoryStore


def test_in_memory_store_saves_raw_messages_before_events():
    store = InMemoryStore()
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        metadata={},
    )
    event = LifeEvent(
        event_id="event-1",
        user_id="user-1",
        event_type=LifeEventType.SLEEP,
        occurred_at=datetime(2026, 7, 1, 2, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 7, 1, 8, 1, tzinfo=UTC),
        source_message_id="msg-1",
        confidence=0.8,
        payload={"sleep_time": "02:00"},
        is_estimate=True,
        confirmation_status="unconfirmed",
    )

    store.messages.save(message)
    store.life_events.save(event)

    assert store.messages.get("msg-1") == message
    assert store.life_events.list_for_user("user-1")[0].source_message_id == "msg-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_in_memory.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.storage`.

- [ ] **Step 3: Add repository interfaces and in-memory store**

Create `src/wechat_agent/storage/repositories.py`:

```python
from __future__ import annotations

from typing import Protocol

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory
from wechat_agent.domain.messages import NormalizedMessage
from wechat_agent.domain.modes import ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus


class MessageRepository(Protocol):
    def save(self, message: NormalizedMessage) -> None: ...
    def get(self, message_id: str) -> NormalizedMessage | None: ...
    def list_recent(self, user_id: str, limit: int) -> list[NormalizedMessage]: ...


class LifeEventRepository(Protocol):
    def save(self, event: LifeEvent) -> None: ...
    def list_for_user(
        self, user_id: str, event_type: LifeEventType | None = None
    ) -> list[LifeEvent]: ...


class MemoryRepository(Protocol):
    def save(self, memory: LongTermMemory) -> None: ...
    def get(self, memory_id: str) -> LongTermMemory | None: ...
    def list_active(self, user_id: str) -> list[LongTermMemory]: ...
    def replace(self, memory: LongTermMemory) -> None: ...


class ModeRepository(Protocol):
    def get(self, user_id: str) -> ModeConfig | None: ...
    def save(self, config: ModeConfig) -> None: ...


class TaskRepository(Protocol):
    def save(self, task: ScheduledTask) -> None: ...
    def list_due(self, user_id: str, now_iso: str) -> list[ScheduledTask]: ...
    def update_status(self, task_id: str, status: TaskStatus) -> None: ...
```

Create `src/wechat_agent/storage/in_memory.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.messages import NormalizedMessage
from wechat_agent.domain.modes import ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus


class InMemoryMessageRepository:
    def __init__(self) -> None:
        self._messages: dict[str, NormalizedMessage] = {}

    def save(self, message: NormalizedMessage) -> None:
        self._messages[message.message_id] = message

    def get(self, message_id: str) -> NormalizedMessage | None:
        return self._messages.get(message_id)

    def list_recent(self, user_id: str, limit: int) -> list[NormalizedMessage]:
        messages = [m for m in self._messages.values() if m.user_id == user_id]
        return sorted(messages, key=lambda m: m.timestamp, reverse=True)[:limit]


class InMemoryLifeEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, LifeEvent] = {}

    def save(self, event: LifeEvent) -> None:
        self._events[event.event_id] = event

    def list_for_user(
        self, user_id: str, event_type: LifeEventType | None = None
    ) -> list[LifeEvent]:
        events = [e for e in self._events.values() if e.user_id == user_id]
        if event_type is not None:
            events = [e for e in events if e.event_type is event_type]
        return sorted(events, key=lambda e: e.recorded_at)


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._memories: dict[str, LongTermMemory] = {}

    def save(self, memory: LongTermMemory) -> None:
        self._memories[memory.memory_id] = memory

    def get(self, memory_id: str) -> LongTermMemory | None:
        return self._memories.get(memory_id)

    def list_active(self, user_id: str) -> list[LongTermMemory]:
        return [
            memory
            for memory in self._memories.values()
            if memory.user_id == user_id and memory.state is MemoryState.ACTIVE
        ]

    def replace(self, memory: LongTermMemory) -> None:
        self._memories[memory.memory_id] = memory


class InMemoryModeRepository:
    def __init__(self) -> None:
        self._configs: dict[str, ModeConfig] = {}

    def get(self, user_id: str) -> ModeConfig | None:
        return self._configs.get(user_id)

    def save(self, config: ModeConfig) -> None:
        self._configs[config.user_id] = config


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}

    def save(self, task: ScheduledTask) -> None:
        self._tasks[task.task_id] = task

    def list_due(self, user_id: str, now_iso: str) -> list[ScheduledTask]:
        return [
            task
            for task in self._tasks.values()
            if task.user_id == user_id
            and task.status is TaskStatus.PENDING
            and task.trigger_at.isoformat() <= now_iso
        ]

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        self._tasks[task_id] = task.model_copy(update={"status": status})


@dataclass
class InMemoryStore:
    messages: InMemoryMessageRepository = field(default_factory=InMemoryMessageRepository)
    life_events: InMemoryLifeEventRepository = field(default_factory=InMemoryLifeEventRepository)
    memories: InMemoryMemoryRepository = field(default_factory=InMemoryMemoryRepository)
    modes: InMemoryModeRepository = field(default_factory=InMemoryModeRepository)
    tasks: InMemoryTaskRepository = field(default_factory=InMemoryTaskRepository)
```

Create `src/wechat_agent/storage/schema.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE raw_messages (
  message_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  direction TEXT NOT NULL,
  message_type TEXT NOT NULL,
  content TEXT,
  media_ref TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  processing_status TEXT NOT NULL DEFAULT 'new'
);

CREATE TABLE life_events (
  event_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL,
  source_message_id TEXT REFERENCES raw_messages(message_id),
  confidence DOUBLE PRECISION NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  is_estimate BOOLEAN NOT NULL,
  confirmation_status TEXT NOT NULL
);

CREATE TABLE long_term_memories (
  memory_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  category TEXT NOT NULL,
  content TEXT NOT NULL,
  importance DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  source_ref TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  state TEXT NOT NULL,
  embedding vector(1536)
);

CREATE TABLE scheduled_tasks (
  task_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  trigger_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  source_message_id TEXT REFERENCES raw_messages(message_id)
);

CREATE TABLE mode_configs (
  user_id TEXT PRIMARY KEY,
  mode TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ,
  do_not_disturb_windows JSONB NOT NULL DEFAULT '[]',
  daily_checkin_windows JSONB NOT NULL DEFAULT '{}',
  tone_preferences JSONB NOT NULL DEFAULT '{}',
  memory_strategy TEXT NOT NULL
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_in_memory.py -v`

Expected: PASS, 1 test.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/storage/repositories.py src/wechat_agent/storage/in_memory.py src/wechat_agent/storage/schema.sql tests/storage/test_in_memory.py
git commit -m "feat: add storage interfaces and in-memory repositories"
```

---

### Task 4: Policy and Mode Engine

**Files:**
- Create: `src/wechat_agent/policy/engine.py`
- Test: `tests/policy/test_engine.py`

**Interfaces:**
- Consumes: `AgentMode`, `ModeConfig`, `TaskType`.
- Produces: `PolicyDecision`, `PolicyEngine.evaluate_checkin(user_id: str, task_type: TaskType, now: datetime) -> PolicyDecision`, `PolicyEngine.get_effective_mode(user_id: str, now: datetime) -> AgentMode`.
- Later tasks use `PolicyDecision.allowed`, `PolicyDecision.reason`, and `PolicyDecision.tone`.

- [ ] **Step 1: Write the failing test**

Create `tests/policy/test_engine.py`:

```python
from datetime import UTC, datetime, timedelta

from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import TaskType
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.storage.in_memory import InMemoryStore


def test_expired_quiet_mode_falls_back_to_daily():
    store = InMemoryStore()
    now = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    store.modes.save(
        ModeConfig(
            user_id="user-1",
            mode=AgentMode.QUIET,
            started_at=now - timedelta(days=1),
            expires_at=now - timedelta(minutes=1),
            do_not_disturb_windows=[],
            daily_checkin_windows={},
            tone_preferences={},
            memory_strategy="explicit_only",
        )
    )

    engine = PolicyEngine(store.modes)

    assert engine.get_effective_mode("user-1", now) is AgentMode.DAILY


def test_quiet_mode_blocks_lunch_checkin_but_allows_user_reminder():
    store = InMemoryStore()
    now = datetime(2026, 7, 1, 12, 30, tzinfo=UTC)
    store.modes.save(
        ModeConfig(
            user_id="user-1",
            mode=AgentMode.QUIET,
            started_at=now,
            expires_at=None,
            do_not_disturb_windows=[],
            daily_checkin_windows={},
            tone_preferences={},
            memory_strategy="explicit_only",
        )
    )
    engine = PolicyEngine(store.modes)

    lunch = engine.evaluate_checkin("user-1", TaskType.LUNCH_MEAL_CHECKIN, now)
    reminder = engine.evaluate_checkin("user-1", TaskType.USER_REMINDER, now)

    assert lunch.allowed is False
    assert lunch.reason == "quiet_mode_blocks_routine_checkin"
    assert reminder.allowed is True
    assert reminder.tone == "gentle"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/policy/test_engine.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.policy`.

- [ ] **Step 3: Add policy engine**

Create `src/wechat_agent/policy/engine.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from wechat_agent.domain.modes import AgentMode
from wechat_agent.domain.tasks import TaskType
from wechat_agent.storage.repositories import ModeRepository


ROUTINE_CHECKINS = {
    TaskType.MORNING_CHECKIN,
    TaskType.LUNCH_MEAL_CHECKIN,
    TaskType.AFTERNOON_ENERGY_CHECKIN,
    TaskType.EVENING_REVIEW,
    TaskType.BEDTIME_WINDDOWN,
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    tone: str
    memory_strategy: str


class PolicyEngine:
    def __init__(self, modes: ModeRepository) -> None:
        self._modes = modes

    def get_effective_mode(self, user_id: str, now: datetime) -> AgentMode:
        config = self._modes.get(user_id)
        if config is None:
            return AgentMode.DAILY
        if config.is_expired(now):
            return AgentMode.DAILY
        return config.mode

    def evaluate_checkin(
        self, user_id: str, task_type: TaskType, now: datetime
    ) -> PolicyDecision:
        mode = self.get_effective_mode(user_id, now)

        if mode is AgentMode.QUIET and task_type in ROUTINE_CHECKINS:
            return PolicyDecision(
                allowed=False,
                reason="quiet_mode_blocks_routine_checkin",
                tone="gentle",
                memory_strategy="explicit_only",
            )

        if mode is AgentMode.COACH:
            return PolicyDecision(
                allowed=True,
                reason="coach_mode_allows_task",
                tone="encouraging",
                memory_strategy="active_tracking",
            )

        if mode is AgentMode.QUIET:
            return PolicyDecision(
                allowed=True,
                reason="quiet_mode_allows_important_task",
                tone="gentle",
                memory_strategy="explicit_only",
            )

        return PolicyDecision(
            allowed=True,
            reason="daily_mode_allows_task",
            tone="warm_daily",
            memory_strategy="routine_auto",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/policy/test_engine.py -v`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/policy/engine.py tests/policy/test_engine.py
git commit -m "feat: add policy and mode engine"
```

---

### Task 5: LLM Gateway Interface and Deterministic Fake Gateway

**Files:**
- Create: `src/wechat_agent/llm/gateway.py`
- Create: `src/wechat_agent/llm/fake_gateway.py`
- Test: `tests/llm/test_fake_gateway.py`

**Interfaces:**
- Produces: `ChatRequest`, `ChatResponse`, `ExtractionResult`, `ImageAnalysisResult`, `EmbeddingResult`, `LLMGateway`.
- Produces fake methods: `FakeLLMGateway.chat`, `extract_life_events`, `analyze_food_image`, `embed`.
- Later tasks depend on deterministic fake outputs.

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_fake_gateway.py`:

```python
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.llm.gateway import ChatRequest


def test_fake_gateway_extracts_sleep_event_from_text():
    gateway = FakeLLMGateway()

    result = gateway.extract_life_events(
        user_id="user-1",
        source_message_id="msg-1",
        text="I slept around 2 and woke up tired.",
    )

    assert result.events[0].event_type == "sleep"
    assert result.events[0].payload["sleep_time"] == "02:00"
    assert result.events[0].confidence == 0.8


def test_fake_gateway_returns_uncertain_food_analysis():
    gateway = FakeLLMGateway()

    result = gateway.analyze_food_image(user_id="user-1", media_ref="meal.jpg")

    assert result.is_estimate is True
    assert "estimated_calories_range" in result.payload


def test_fake_gateway_chat_uses_tone_and_intent():
    gateway = FakeLLMGateway()
    response = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="morning_checkin",
            tone="warm_daily",
            user_text=None,
            memories=[],
            recent_messages=[],
            facts={"goal": "collect_sleep_and_mood"},
        )
    )

    assert "How did you sleep last night" in response.content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/llm/test_fake_gateway.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.llm`.

- [ ] **Step 3: Add gateway models and fake implementation**

Create `src/wechat_agent/llm/gateway.py`:

```python
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str
    intent: str
    tone: str
    user_text: str | None
    memories: list[str] = Field(default_factory=list)
    recent_messages: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    content: str
    used_memory_ids: list[str] = Field(default_factory=list)
    risk_level: str = "normal"


class ExtractedEvent(BaseModel):
    event_type: str
    payload: dict[str, Any]
    confidence: float
    is_estimate: bool


class ExtractionResult(BaseModel):
    events: list[ExtractedEvent]
    long_term_memory_candidates: list[str] = Field(default_factory=list)
    needs_follow_up: bool = False
    follow_up_question: str | None = None


class ImageAnalysisResult(BaseModel):
    payload: dict[str, Any]
    confidence: float
    is_estimate: bool


class EmbeddingResult(BaseModel):
    embedding: list[float]


class LLMGateway(Protocol):
    def chat(self, request: ChatRequest) -> ChatResponse: ...
    def extract_life_events(
        self, user_id: str, source_message_id: str, text: str
    ) -> ExtractionResult: ...
    def analyze_food_image(self, user_id: str, media_ref: str) -> ImageAnalysisResult: ...
    def embed(self, text: str) -> EmbeddingResult: ...
```

Create `src/wechat_agent/llm/fake_gateway.py`:

```python
from __future__ import annotations

from wechat_agent.llm.gateway import (
    ChatRequest,
    ChatResponse,
    EmbeddingResult,
    ExtractedEvent,
    ExtractionResult,
    ImageAnalysisResult,
)


class FakeLLMGateway:
    def chat(self, request: ChatRequest) -> ChatResponse:
        if request.intent == "morning_checkin":
            return ChatResponse(content="Morning. How did you sleep last night? Any dreams?")
        if request.intent == "food_photo_response":
            return ChatResponse(content="I will save this as an estimate, not a precise measurement.")
        if request.intent == "reminder_confirmation":
            return ChatResponse(content="Got it. I will remind you when it is time.")
        return ChatResponse(content="I am here. Take your time.")

    def extract_life_events(
        self, user_id: str, source_message_id: str, text: str
    ) -> ExtractionResult:
        lowered = text.lower()
        events: list[ExtractedEvent] = []
        if "slept" in lowered or "sleep" in lowered:
            events.append(
                ExtractedEvent(
                    event_type="sleep",
                    payload={"sleep_time": "02:00", "waking_state": "tired"},
                    confidence=0.8,
                    is_estimate=True,
                )
            )
        if "remind" in lowered:
            events.append(
                ExtractedEvent(
                    event_type="reminder",
                    payload={"content": text, "time_text": "tomorrow morning"},
                    confidence=0.7,
                    is_estimate=True,
                )
            )
        return ExtractionResult(events=events)

    def analyze_food_image(self, user_id: str, media_ref: str) -> ImageAnalysisResult:
        return ImageAnalysisResult(
            payload={
                "foods": ["rice", "chicken", "vegetables"],
                "estimated_calories_range": [550, 750],
                "protein": "medium",
                "carbs": "medium_high",
                "fat": "medium",
            },
            confidence=0.65,
            is_estimate=True,
        )

    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(embedding=[float(min(len(text), 100)) / 100.0, 0.0, 1.0])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/llm/test_fake_gateway.py -v`

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/llm/gateway.py src/wechat_agent/llm/fake_gateway.py tests/llm/test_fake_gateway.py
git commit -m "feat: add llm gateway abstraction"
```

---

### Task 6: Memory Service for Raw Messages, Events, Long-Term Memory, and Corrections

**Files:**
- Create: `src/wechat_agent/memory/service.py`
- Test: `tests/memory/test_service.py`

**Interfaces:**
- Consumes: `InMemoryStore`, `LLMGateway`, `NormalizedMessage`.
- Produces: `MemoryService.save_raw_message(message: NormalizedMessage) -> None`, `extract_and_store(message: NormalizedMessage) -> list[LifeEvent]`, `recall(user_id: str, query: str, limit: int = 5) -> list[LongTermMemory]`, `forget_memory(memory_id: str) -> None`.
- Later tasks use `save_raw_message`, `extract_and_store`, and `recall`.

- [ ] **Step 1: Write the failing test**

Create `tests/memory/test_service.py`:

```python
from datetime import UTC, datetime

from wechat_agent.domain.events import LifeEventType
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.storage.in_memory import InMemoryStore


def test_memory_service_saves_raw_message_before_extracted_event():
    store = InMemoryStore()
    service = MemoryService(store=store, llm=FakeLLMGateway())
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2 and woke up tired.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        metadata={},
    )

    events = service.extract_and_store(message)

    assert store.messages.get("msg-1") == message
    assert events[0].event_type is LifeEventType.SLEEP
    assert store.life_events.list_for_user("user-1")[0].source_message_id == "msg-1"


def test_forget_memory_marks_memory_denied():
    store = InMemoryStore()
    service = MemoryService(store=store, llm=FakeLLMGateway())
    memory = service.remember_candidate(
        user_id="user-1",
        category="preference",
        content="User prefers gentle reminders.",
        source_ref="msg-1",
    )

    service.forget_memory(memory.memory_id)

    assert store.memories.list_active("user-1") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/memory/test_service.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.memory`.

- [ ] **Step 3: Add memory service**

Create `src/wechat_agent/memory/service.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.messages import MessageType, NormalizedMessage
from wechat_agent.llm.gateway import LLMGateway
from wechat_agent.storage.in_memory import InMemoryStore


class MemoryService:
    def __init__(self, store: InMemoryStore, llm: LLMGateway) -> None:
        self._store = store
        self._llm = llm

    def save_raw_message(self, message: NormalizedMessage) -> None:
        self._store.messages.save(message)

    def extract_and_store(self, message: NormalizedMessage) -> list[LifeEvent]:
        self.save_raw_message(message)
        if message.message_type is not MessageType.TEXT or not message.content:
            return []

        extraction = self._llm.extract_life_events(
            user_id=message.user_id,
            source_message_id=message.message_id,
            text=message.content,
        )
        events: list[LifeEvent] = []
        for extracted in extraction.events:
            event = LifeEvent(
                event_id=f"event-{uuid4()}",
                user_id=message.user_id,
                event_type=LifeEventType(extracted.event_type),
                occurred_at=message.timestamp,
                recorded_at=datetime.now(UTC),
                source_message_id=message.message_id,
                confidence=extracted.confidence,
                payload=extracted.payload,
                is_estimate=extracted.is_estimate,
                confirmation_status="unconfirmed",
            )
            self._store.life_events.save(event)
            events.append(event)
        return events

    def remember_candidate(
        self, user_id: str, category: str, content: str, source_ref: str
    ) -> LongTermMemory:
        embedding = self._llm.embed(content).embedding
        memory = LongTermMemory(
            memory_id=f"mem-{uuid4()}",
            user_id=user_id,
            category=category,
            content=content,
            importance=0.7,
            confidence=0.8,
            source_ref=source_ref,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            state=MemoryState.ACTIVE,
            embedding=embedding,
        )
        self._store.memories.save(memory)
        return memory

    def recall(self, user_id: str, query: str, limit: int = 5) -> list[LongTermMemory]:
        memories = self._store.memories.list_active(user_id)
        return memories[:limit]

    def forget_memory(self, memory_id: str) -> None:
        memory = self._store.memories.get(memory_id)
        if memory is None:
            return
        self._store.memories.replace(memory.model_copy(update={"state": MemoryState.DENIED}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/memory/test_service.py -v`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/memory/service.py tests/memory/test_service.py
git commit -m "feat: add memory service"
```

---

### Task 7: Scheduler Service for Check-In Windows and Reminders

**Files:**
- Create: `src/wechat_agent/scheduler/service.py`
- Test: `tests/scheduler/test_service.py`

**Interfaces:**
- Consumes: `InMemoryStore`, `PolicyEngine`, `ScheduledTask`, `TaskType`, `TaskStatus`.
- Produces: `SchedulerService.create_daily_checkins(user_id: str, conversation_id: str, channel: str, day: date) -> list[ScheduledTask]`, `SchedulerService.due_allowed_tasks(user_id: str, now: datetime) -> list[ScheduledTask]`, `SchedulerService.create_user_reminder(...) -> ScheduledTask`.
- Later tasks consume `due_allowed_tasks`.

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_service.py`:

```python
from datetime import UTC, date, datetime

from wechat_agent.domain.tasks import TaskStatus, TaskType
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def test_scheduler_creates_five_daily_checkins():
    store = InMemoryStore()
    service = SchedulerService(store=store, policy=PolicyEngine(store.modes))

    tasks = service.create_daily_checkins(
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        day=date(2026, 7, 1),
    )

    assert [task.task_type for task in tasks] == [
        TaskType.MORNING_CHECKIN,
        TaskType.LUNCH_MEAL_CHECKIN,
        TaskType.AFTERNOON_ENERGY_CHECKIN,
        TaskType.EVENING_REVIEW,
        TaskType.BEDTIME_WINDDOWN,
    ]


def test_due_allowed_tasks_returns_pending_daily_task():
    store = InMemoryStore()
    service = SchedulerService(store=store, policy=PolicyEngine(store.modes))
    service.create_daily_checkins("user-1", "conv-1", "test", date(2026, 7, 1))

    due = service.due_allowed_tasks("user-1", datetime(2026, 7, 1, 8, 1, tzinfo=UTC))

    assert len(due) == 1
    assert due[0].status is TaskStatus.PENDING
    assert due[0].task_type is TaskType.MORNING_CHECKIN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/scheduler/test_service.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.scheduler`.

- [ ] **Step 3: Add scheduler service**

Create `src/wechat_agent/scheduler/service.py`:

```python
from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import uuid4

from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.storage.in_memory import InMemoryStore


DAILY_CHECKINS: list[tuple[TaskType, time, dict[str, str]]] = [
    (TaskType.MORNING_CHECKIN, time(8, 0), {"goal": "collect_sleep_and_mood"}),
    (TaskType.LUNCH_MEAL_CHECKIN, time(12, 30), {"goal": "collect_meal"}),
    (TaskType.AFTERNOON_ENERGY_CHECKIN, time(15, 30), {"goal": "check_energy_and_plan"}),
    (TaskType.EVENING_REVIEW, time(20, 30), {"goal": "review_day_and_tomorrow"}),
    (TaskType.BEDTIME_WINDDOWN, time(23, 0), {"goal": "sleep_preparation"}),
]


class SchedulerService:
    def __init__(self, store: InMemoryStore, policy: PolicyEngine) -> None:
        self._store = store
        self._policy = policy

    def create_daily_checkins(
        self, user_id: str, conversation_id: str, channel: str, day: date
    ) -> list[ScheduledTask]:
        tasks: list[ScheduledTask] = []
        for task_type, trigger_time, payload in DAILY_CHECKINS:
            task = ScheduledTask(
                task_id=f"task-{uuid4()}",
                user_id=user_id,
                conversation_id=conversation_id,
                channel=channel,
                task_type=task_type,
                status=TaskStatus.PENDING,
                trigger_at=datetime.combine(day, trigger_time, tzinfo=UTC),
                payload=payload,
                source_message_id=None,
            )
            self._store.tasks.save(task)
            tasks.append(task)
        return tasks

    def create_user_reminder(
        self,
        user_id: str,
        conversation_id: str,
        channel: str,
        trigger_at: datetime,
        content: str,
        source_message_id: str | None,
    ) -> ScheduledTask:
        task = ScheduledTask(
            task_id=f"task-{uuid4()}",
            user_id=user_id,
            conversation_id=conversation_id,
            channel=channel,
            task_type=TaskType.USER_REMINDER,
            status=TaskStatus.PENDING,
            trigger_at=trigger_at,
            payload={"content": content},
            source_message_id=source_message_id,
        )
        self._store.tasks.save(task)
        return task

    def due_allowed_tasks(self, user_id: str, now: datetime) -> list[ScheduledTask]:
        due = self._store.tasks.list_due(user_id, now.isoformat())
        allowed: list[ScheduledTask] = []
        for task in due:
            decision = self._policy.evaluate_checkin(user_id, task.task_type, now)
            if decision.allowed:
                allowed.append(task)
        return allowed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/scheduler/test_service.py -v`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/scheduler/service.py tests/scheduler/test_service.py
git commit -m "feat: add scheduler service"
```

---

### Task 8: Agent Orchestrator for Text, Image, Reminder, and Scheduled Intents

**Files:**
- Create: `src/wechat_agent/agent/orchestrator.py`
- Test: `tests/agent/test_orchestrator.py`

**Interfaces:**
- Consumes: `MemoryService`, `SchedulerService`, `PolicyEngine`, `LLMGateway`, `NormalizedMessage`, `ScheduledTask`.
- Produces: `AgentOrchestrator.handle_message(message: NormalizedMessage) -> OutgoingMessage`, `AgentOrchestrator.handle_scheduled_task(task: ScheduledTask, now: datetime) -> OutgoingMessage`.
- Later test channel and e2e tests consume both methods.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_orchestrator.py`:

```python
from datetime import UTC, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def build_orchestrator():
    store = InMemoryStore()
    llm = FakeLLMGateway()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    return AgentOrchestrator(store, llm, memory, scheduler, policy), store


def test_text_message_is_saved_and_sleep_event_is_extracted():
    orchestrator, store = build_orchestrator()
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2 and woke up tired.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        metadata={},
    )

    reply = orchestrator.handle_message(message)

    assert "Take your time" in reply.content
    assert store.messages.get("msg-1") == message
    assert len(store.life_events.list_for_user("user-1")) == 1


def test_image_message_creates_estimated_meal_event():
    orchestrator, store = build_orchestrator()
    message = NormalizedMessage(
        message_id="msg-2",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.IMAGE,
        content=None,
        media_ref="meal.jpg",
        timestamp=datetime(2026, 7, 1, 12, 35, tzinfo=UTC),
        metadata={},
    )

    reply = orchestrator.handle_message(message)

    assert "estimate" in reply.content
    assert store.life_events.list_for_user("user-1")[0].payload["foods"] == [
        "rice",
        "chicken",
        "vegetables",
    ]


def test_scheduled_morning_checkin_generates_natural_message():
    orchestrator, _store = build_orchestrator()
    task = ScheduledTask(
        task_id="task-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        task_type=TaskType.MORNING_CHECKIN,
        status=TaskStatus.PENDING,
        trigger_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        payload={"goal": "collect_sleep_and_mood"},
        source_message_id=None,
    )

    outgoing = orchestrator.handle_scheduled_task(
        task, now=datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    )

    assert "How did you sleep last night" in outgoing.content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent/test_orchestrator.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.agent`.

- [ ] **Step 3: Add orchestrator**

Create `src/wechat_agent/agent/orchestrator.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.messages import MessageType, NormalizedMessage, OutgoingMessage
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus
from wechat_agent.llm.gateway import ChatRequest, LLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


class AgentOrchestrator:
    def __init__(
        self,
        store: InMemoryStore,
        llm: LLMGateway,
        memory: MemoryService,
        scheduler: SchedulerService,
        policy: PolicyEngine,
    ) -> None:
        self._store = store
        self._llm = llm
        self._memory = memory
        self._scheduler = scheduler
        self._policy = policy

    def handle_message(self, message: NormalizedMessage) -> OutgoingMessage:
        if message.message_type is MessageType.IMAGE and message.media_ref:
            self._memory.save_raw_message(message)
            analysis = self._llm.analyze_food_image(message.user_id, message.media_ref)
            event = LifeEvent(
                event_id=f"event-{uuid4()}",
                user_id=message.user_id,
                event_type=LifeEventType.MEAL,
                occurred_at=message.timestamp,
                recorded_at=datetime.now(UTC),
                source_message_id=message.message_id,
                confidence=analysis.confidence,
                payload=analysis.payload,
                is_estimate=analysis.is_estimate,
                confirmation_status="unconfirmed",
            )
            self._store.life_events.save(event)
            response = self._llm.chat(
                ChatRequest(
                    user_id=message.user_id,
                    intent="food_photo_response",
                    tone="warm_daily",
                    user_text=None,
                    facts=analysis.payload,
                )
            )
            return OutgoingMessage(
                conversation_id=message.conversation_id,
                channel=message.channel,
                content=response.content,
                metadata={"intent": "food_photo_response"},
            )

        events = self._memory.extract_and_store(message)
        intent = "reminder_confirmation" if any(e.event_type is LifeEventType.REMINDER for e in events) else "chat"
        response = self._llm.chat(
            ChatRequest(
                user_id=message.user_id,
                intent=intent,
                tone="warm_daily",
                user_text=message.content,
                memories=[m.content for m in self._memory.recall(message.user_id, message.content or "")],
                recent_messages=[],
                facts={"event_count": len(events)},
            )
        )
        return OutgoingMessage(
            conversation_id=message.conversation_id,
            channel=message.channel,
            content=response.content,
            metadata={"intent": intent},
        )

    def handle_scheduled_task(self, task: ScheduledTask, now: datetime) -> OutgoingMessage:
        decision = self._policy.evaluate_checkin(task.user_id, task.task_type, now)
        response = self._llm.chat(
            ChatRequest(
                user_id=task.user_id,
                intent=task.task_type.value,
                tone=decision.tone,
                user_text=None,
                memories=[m.content for m in self._memory.recall(task.user_id, task.task_type.value)],
                recent_messages=[],
                facts=task.payload,
            )
        )
        self._store.tasks.update_status(task.task_id, TaskStatus.SENT)
        return OutgoingMessage(
            conversation_id=task.conversation_id,
            channel=task.channel,
            content=response.content,
            metadata={"task_id": task.task_id, "intent": task.task_type.value},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent/test_orchestrator.py -v`

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add src/wechat_agent/agent/orchestrator.py tests/agent/test_orchestrator.py
git commit -m "feat: add agent orchestrator"
```

---

### Task 9: Test Channel and End-to-End MVP Flow

**Files:**
- Create: `src/wechat_agent/channels/base.py`
- Create: `src/wechat_agent/channels/test_channel.py`
- Create: `src/wechat_agent/observability/metrics.py`
- Modify: `README.md`
- Test: `tests/channels/test_test_channel.py`
- Test: `tests/e2e/test_personal_life_agent_flow.py`

**Interfaces:**
- Consumes: `AgentOrchestrator`, `NormalizedMessage`, `OutgoingMessage`.
- Produces: `ChannelAdapter`, `TestChannelAdapter.receive_text`, `receive_image`, `sent_messages`, `Metrics`.
- This task provides the seven-day test-channel foundation required by the spec.

- [ ] **Step 1: Write failing channel tests**

Create `tests/channels/test_test_channel.py`:

```python
from datetime import UTC, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.channels.test_channel import TestChannelAdapter
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def build_channel():
    store = InMemoryStore()
    llm = FakeLLMGateway()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    orchestrator = AgentOrchestrator(store, llm, memory, scheduler, policy)
    return TestChannelAdapter(orchestrator=orchestrator), store


def test_test_channel_receives_text_and_sends_reply():
    channel, store = build_channel()

    reply = channel.receive_text(
        user_id="user-1",
        conversation_id="conv-1",
        content="I slept around 2.",
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
    )

    assert reply in channel.sent_messages
    assert len(store.life_events.list_for_user("user-1")) == 1
```

Create `tests/e2e/test_personal_life_agent_flow.py`:

```python
from datetime import UTC, date, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.channels.test_channel import TestChannelAdapter
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def test_e2e_daily_checkin_sleep_reply_and_food_photo_flow():
    store = InMemoryStore()
    llm = FakeLLMGateway()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    orchestrator = AgentOrchestrator(store, llm, memory, scheduler, policy)
    channel = TestChannelAdapter(orchestrator=orchestrator)

    scheduler.create_daily_checkins("user-1", "conv-1", "test", date(2026, 7, 1))
    due = scheduler.due_allowed_tasks("user-1", datetime(2026, 7, 1, 8, 1, tzinfo=UTC))
    morning = orchestrator.handle_scheduled_task(
        due[0], now=datetime(2026, 7, 1, 8, 1, tzinfo=UTC)
    )
    channel.send(morning)

    channel.receive_text(
        user_id="user-1",
        conversation_id="conv-1",
        content="I slept around 2 and woke up tired.",
        timestamp=datetime(2026, 7, 1, 8, 5, tzinfo=UTC),
    )
    channel.receive_image(
        user_id="user-1",
        conversation_id="conv-1",
        media_ref="meal.jpg",
        timestamp=datetime(2026, 7, 1, 12, 40, tzinfo=UTC),
    )

    event_types = [event.event_type.value for event in store.life_events.list_for_user("user-1")]
    assert event_types == ["sleep", "meal"]
    assert len(channel.sent_messages) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/channels/test_test_channel.py tests/e2e/test_personal_life_agent_flow.py -v`

Expected: FAIL with `ModuleNotFoundError` for `wechat_agent.channels`.

- [ ] **Step 3: Add channel interface, test adapter, and metrics**

Create `src/wechat_agent/channels/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from wechat_agent.domain.messages import NormalizedMessage, OutgoingMessage


class ChannelAdapter(Protocol):
    def normalize(self, raw: dict[str, object]) -> NormalizedMessage: ...
    def send(self, message: OutgoingMessage) -> None: ...
```

Create `src/wechat_agent/channels/test_channel.py`:

```python
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.domain.messages import (
    MessageDirection,
    MessageType,
    NormalizedMessage,
    OutgoingMessage,
)


class TestChannelAdapter:
    def __init__(self, orchestrator: AgentOrchestrator) -> None:
        self._orchestrator = orchestrator
        self.sent_messages: list[OutgoingMessage] = []

    def normalize(self, raw: dict[str, object]) -> NormalizedMessage:
        return NormalizedMessage(
            message_id=str(raw["message_id"]),
            user_id=str(raw["user_id"]),
            conversation_id=str(raw["conversation_id"]),
            channel="test",
            direction=MessageDirection.INBOUND,
            message_type=MessageType(str(raw["message_type"])),
            content=raw.get("content") if isinstance(raw.get("content"), str) else None,
            media_ref=raw.get("media_ref") if isinstance(raw.get("media_ref"), str) else None,
            timestamp=raw["timestamp"],
            metadata={"raw": "test_channel"},
        )

    def send(self, message: OutgoingMessage) -> None:
        self.sent_messages.append(message)

    def receive_text(
        self, user_id: str, conversation_id: str, content: str, timestamp: datetime
    ) -> OutgoingMessage:
        message = self.normalize(
            {
                "message_id": f"msg-{uuid4()}",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_type": "text",
                "content": content,
                "timestamp": timestamp,
            }
        )
        reply = self._orchestrator.handle_message(message)
        self.send(reply)
        return reply

    def receive_image(
        self, user_id: str, conversation_id: str, media_ref: str, timestamp: datetime
    ) -> OutgoingMessage:
        message = self.normalize(
            {
                "message_id": f"msg-{uuid4()}",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_type": "image",
                "media_ref": media_ref,
                "timestamp": timestamp,
            }
        )
        reply = self._orchestrator.handle_message(message)
        self.send(reply)
        return reply
```

Create `src/wechat_agent/observability/metrics.py`:

```python
from __future__ import annotations

from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self._counter: Counter[str] = Counter()

    def increment(self, name: str, amount: int = 1) -> None:
        self._counter[name] += amount

    def get(self, name: str) -> int:
        return self._counter[name]
```

- [ ] **Step 4: Update README with test-channel MVP usage**

Modify `README.md` to contain:

````markdown
# WechatAgent

WechatAgent is a channel-independent personal life Agent prototype.

The first implementation target is a modular Python monolith with:

- normalized message adapters
- Agent orchestration
- memory and life event extraction
- daily scheduling
- quiet, daily, and coach modes
- an LLM gateway abstraction
- a deterministic test channel

The first runnable channel is `TestChannelAdapter`; direct personal WeChat integration is intentionally deferred until the core Agent behavior is stable.

## Development

Install in editable mode:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -v
```
````

- [ ] **Step 5: Run all tests**

Run: `pytest -v`

Expected: PASS for all tests created in Tasks 1-9.

- [ ] **Step 6: Run ruff**

Run: `ruff check .`

Expected: PASS with `All checks passed!`.

- [ ] **Step 7: Commit**

```bash
git add src/wechat_agent/channels/base.py src/wechat_agent/channels/test_channel.py src/wechat_agent/observability/metrics.py README.md tests/channels/test_test_channel.py tests/e2e/test_personal_life_agent_flow.py
git commit -m "feat: add test channel and e2e agent flow"
```

---

## Self-Review Notes

Spec coverage:

- Natural text conversation: Task 8 and Task 9.
- Proactive daily check-ins: Task 7, Task 8, Task 9.
- Sleep and dream logging foundation: Task 2, Task 5, Task 6, Task 8.
- Meal logging with food photo analysis: Task 5 and Task 8.
- Mood, energy, body state, and plan logging foundation: Task 2 and Task 6; additional extraction patterns can extend `FakeLLMGateway` and provider implementations after the first vertical slice.
- Reminder creation and delivery foundation: Task 2, Task 5, Task 7, Task 8.
- Long-term memory: Task 2, Task 3, Task 6.
- Daily and weekly summaries foundation: Task 2, Task 7; summary generation is represented in the LLM Gateway interface.
- Manual mode switching foundation: Task 2, Task 3, Task 4.
- Channel-independent abstraction: Task 1 and Task 9.
- PostgreSQL and pgvector target: Task 3 schema.
- Remote model gateway abstraction: Task 5.
- Safety and risk boundaries foundation: Task 4 policy boundaries and Task 5 risk classification interface; health-specific provider behavior should be added before enabling real model responses.

Type consistency:

- `NormalizedMessage`, `OutgoingMessage`, `LifeEvent`, `LongTermMemory`, `ModeConfig`, and `ScheduledTask` are defined before use.
- `InMemoryStore` exposes `messages`, `life_events`, `memories`, `modes`, and `tasks`.
- `AgentOrchestrator` consumes the exact service methods defined in earlier tasks.
- `TestChannelAdapter` calls `AgentOrchestrator.handle_message` and stores `OutgoingMessage` instances.

The plan was scanned for banned incomplete-work markers after writing.
