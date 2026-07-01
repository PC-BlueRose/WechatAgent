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
