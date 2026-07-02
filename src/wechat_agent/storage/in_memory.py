from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.messages import NormalizedMessage
from wechat_agent.domain.modes import ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus
from wechat_agent.storage.store import Store


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
        now = datetime.fromisoformat(now_iso)
        return [
            task
            for task in self._tasks.values()
            if task.user_id == user_id
            and task.status is TaskStatus.PENDING
            and task.trigger_at <= now
        ]

    def status_counts(self, user_id: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for task in self._tasks.values():
            if task.user_id != user_id:
                continue
            counts[task.status.value] = counts.get(task.status.value, 0) + 1
        return counts

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        self._tasks[task_id] = task.model_copy(update={"status": status})


@dataclass
class InMemoryStore(Store):
    messages: InMemoryMessageRepository = field(default_factory=InMemoryMessageRepository)
    life_events: InMemoryLifeEventRepository = field(default_factory=InMemoryLifeEventRepository)
    memories: InMemoryMemoryRepository = field(default_factory=InMemoryMemoryRepository)
    modes: InMemoryModeRepository = field(default_factory=InMemoryModeRepository)
    tasks: InMemoryTaskRepository = field(default_factory=InMemoryTaskRepository)
