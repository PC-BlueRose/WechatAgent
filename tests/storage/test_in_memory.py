from datetime import UTC, datetime

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.storage.in_memory import InMemoryStore


def test_in_memory_store_saves_raw_messages_before_events():
    store = InMemoryStore()
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        metadata={},
    )
    event = LifeEvent(
        event_id="event-1",
        user_id="user-1",
        event_type=LifeEventType.SLEEP,
        occurred_at=datetime(2026, 7, 1, 2, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 7, 1, 8, 1, tzinfo=UTC),
        source_message_id="msg-1",
        confidence=0.8,
        payload={"sleep_time": "02:00"},
        is_estimate=True,
        confirmation_status="unconfirmed",
    )

    store.messages.save(message)
    store.life_events.save(event)

    assert store.messages.get("msg-1") == message
    assert store.life_events.list_for_user("user-1")[0].source_message_id == "msg-1"


def test_in_memory_store_lists_due_tasks_using_datetime_comparison():
    store = InMemoryStore()
    task = ScheduledTask(
        task_id="task-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        task_type=TaskType.USER_REMINDER,
        status=TaskStatus.PENDING,
        trigger_at=datetime(2026, 7, 1, 9, 30, tzinfo=UTC),
        payload={},
        source_message_id=None,
    )

    store.tasks.save(task)

    assert store.tasks.list_due("user-1", "2026-07-01T10:00:00+01:00") == []
