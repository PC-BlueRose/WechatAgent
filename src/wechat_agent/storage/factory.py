from __future__ import annotations

from wechat_agent.config import DatabaseSettings
from wechat_agent.storage.in_memory import InMemoryStore
from wechat_agent.storage.postgres import build_postgres_store
from wechat_agent.storage.store import Store


def build_store(settings: DatabaseSettings) -> Store:
    if settings.backend == "inmemory":
        return InMemoryStore()
    return build_postgres_store(settings)
