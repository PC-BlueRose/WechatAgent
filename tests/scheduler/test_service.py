from datetime import UTC, date, datetime

from wechat_agent.domain.tasks import TaskStatus, TaskType
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def test_scheduler_creates_five_daily_checkins():
    store = InMemoryStore()
    service = SchedulerService(store=store, policy=PolicyEngine(store.modes))

    tasks = service.create_daily_checkins(
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        day=date(2026, 7, 1),
    )

    assert [task.task_type for task in tasks] == [
        TaskType.MORNING_CHECKIN,
        TaskType.LUNCH_MEAL_CHECKIN,
        TaskType.AFTERNOON_ENERGY_CHECKIN,
        TaskType.EVENING_REVIEW,
        TaskType.BEDTIME_WINDDOWN,
    ]


def test_due_allowed_tasks_returns_pending_daily_task():
    store = InMemoryStore()
    service = SchedulerService(store=store, policy=PolicyEngine(store.modes))
    service.create_daily_checkins("user-1", "conv-1", "test", date(2026, 7, 1))

    due = service.due_allowed_tasks("user-1", datetime(2026, 7, 1, 8, 1, tzinfo=UTC))

    assert len(due) == 1
    assert due[0].status is TaskStatus.PENDING
    assert due[0].task_type is TaskType.MORNING_CHECKIN
