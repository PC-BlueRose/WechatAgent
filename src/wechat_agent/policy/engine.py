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
