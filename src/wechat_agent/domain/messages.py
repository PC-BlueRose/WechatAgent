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
