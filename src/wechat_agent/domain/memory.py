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
