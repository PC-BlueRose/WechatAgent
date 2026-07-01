from datetime import UTC, datetime, timedelta

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType


def test_life_event_carries_payload_confidence_and_estimate_flag():
    event = LifeEvent(
        event_id="event-1",
        user_id="user-1",
        event_type=LifeEventType.SLEEP,
        occurred_at=datetime(2026, 7, 1, 2, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 7, 1, 8, 30, tzinfo=UTC),
        source_message_id="msg-1",
        confidence=0.84,
        payload={"sleep_time": "02:00", "waking_state": "tired"},
        is_estimate=True,
        confirmation_status="unconfirmed",
    )

    assert event.event_type is LifeEventType.SLEEP
    assert event.payload["waking_state"] == "tired"
    assert event.is_estimate is True


def test_long_term_memory_can_be_deprecated():
    memory = LongTermMemory(
        memory_id="mem-1",
        user_id="user-1",
        category="preference",
        content="User prefers gentle reminders.",
        importance=0.7,
        confidence=0.9,
        source_ref="msg-1",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
        updated_at=datetime(2026, 7, 1, tzinfo=UTC),
        state=MemoryState.DEPRECATED,
        embedding=None,
    )

    assert memory.state is MemoryState.DEPRECATED


def test_mode_config_can_expire():
    now = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    config = ModeConfig(
        user_id="user-1",
        mode=AgentMode.QUIET,
        started_at=now - timedelta(hours=2),
        expires_at=now - timedelta(minutes=1),
        do_not_disturb_windows=[],
        daily_checkin_windows={"morning": ["07:30", "10:30"]},
        tone_preferences={"default": "gentle"},
        memory_strategy="explicit_only",
    )

    assert config.is_expired(now) is True


def test_scheduled_task_tracks_status_and_intent():
    task = ScheduledTask(
        task_id="task-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        task_type=TaskType.MORNING_CHECKIN,
        status=TaskStatus.PENDING,
        trigger_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        payload={"goal": "collect_sleep_and_mood"},
        source_message_id=None,
    )

    assert task.task_type is TaskType.MORNING_CHECKIN
    assert task.payload["goal"] == "collect_sleep_and_mood"
