from __future__ import annotations

from dataclasses import dataclass

from wechat_agent.storage.repositories import (
    LifeEventRepository,
    MemoryRepository,
    MessageRepository,
    ModeRepository,
    TaskRepository,
)


@dataclass
class Store:
    messages: MessageRepository
    life_events: LifeEventRepository
    memories: MemoryRepository
    modes: ModeRepository
    tasks: TaskRepository
