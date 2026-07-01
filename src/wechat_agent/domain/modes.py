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
