from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import uuid4

from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.storage.store import Store


DAILY_CHECKINS: list[tuple[TaskType, time, dict[str, str]]] = [
    (TaskType.MORNING_CHECKIN, time(8, 0), {"goal": "collect_sleep_and_mood"}),
    (TaskType.LUNCH_MEAL_CHECKIN, time(12, 30), {"goal": "collect_meal"}),
    (
        TaskType.AFTERNOON_ENERGY_CHECKIN,
        time(15, 30),
        {"goal": "check_energy_and_plan"},
    ),
    (TaskType.EVENING_REVIEW, time(20, 30), {"goal": "review_day_and_tomorrow"}),
    (TaskType.BEDTIME_WINDDOWN, time(23, 0), {"goal": "sleep_preparation"}),
]


class SchedulerService:
    def __init__(self, store: Store, policy: PolicyEngine) -> None:
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
                continue
            self._store.tasks.update_status(task.task_id, TaskStatus.EXPIRED)
        return allowed
