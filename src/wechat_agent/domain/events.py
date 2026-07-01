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
