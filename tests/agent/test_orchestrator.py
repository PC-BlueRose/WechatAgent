from datetime import UTC, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def build_orchestrator():
    store = InMemoryStore()
    llm = FakeLLMGateway()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    return AgentOrchestrator(store, llm, memory, scheduler, policy), store


def test_text_message_is_saved_and_sleep_event_is_extracted():
    orchestrator, store = build_orchestrator()
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2 and woke up tired.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        metadata={},
    )

    reply = orchestrator.handle_message(message)

    assert "Take your time" in reply.content
    assert store.messages.get("msg-1") == message
    assert len(store.life_events.list_for_user("user-1")) == 1


def test_reminder_message_schedules_user_reminder_task():
    orchestrator, store = build_orchestrator()
    message = NormalizedMessage(
        message_id="msg-3",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="Remind me tomorrow morning to stretch.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 20, 15, tzinfo=UTC),
        metadata={},
    )

    reply = orchestrator.handle_message(message)
    due = store.tasks.list_due("user-1", datetime(2026, 7, 2, 8, 1, tzinfo=UTC).isoformat())

    assert "remind you" in reply.content
    assert len(due) == 1
    assert due[0].task_type is TaskType.USER_REMINDER
    assert due[0].status is TaskStatus.PENDING
    assert due[0].trigger_at == datetime(2026, 7, 2, 8, 0, tzinfo=UTC)
    assert due[0].payload["content"] == "Remind me tomorrow morning to stretch."
    assert due[0].source_message_id == "msg-3"


def test_image_message_creates_estimated_meal_event():
    orchestrator, store = build_orchestrator()
    message = NormalizedMessage(
        message_id="msg-2",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.IMAGE,
        content=None,
        media_ref="meal.jpg",
        timestamp=datetime(2026, 7, 1, 12, 35, tzinfo=UTC),
        metadata={},
    )

    reply = orchestrator.handle_message(message)

    assert "estimate" in reply.content
    assert store.life_events.list_for_user("user-1")[0].payload["foods"] == [
        "rice",
        "chicken",
        "vegetables",
    ]


def test_scheduled_morning_checkin_generates_natural_message():
    orchestrator, _store = build_orchestrator()
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

    outgoing = orchestrator.handle_scheduled_task(
        task, now=datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    )

    assert "How did you sleep last night" in outgoing.content


def test_scheduled_user_reminder_delivers_original_reminder_content():
    orchestrator, store = build_orchestrator()
    now = datetime(2026, 7, 2, 8, 0, tzinfo=UTC)
    task = ScheduledTask(
        task_id="task-reminder-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        task_type=TaskType.USER_REMINDER,
        status=TaskStatus.PENDING,
        trigger_at=now,
        payload={"content": "Take your vitamins."},
        source_message_id="msg-42",
    )
    store.tasks.save(task)

    outgoing = orchestrator.handle_scheduled_task(task, now=now)

    assert outgoing.content == "Take your vitamins."
    assert outgoing.metadata["intent"] == "user_reminder"
    assert store.tasks.list_due("user-1", now.isoformat()) == []


def test_quiet_mode_suppresses_routine_scheduled_checkin():
    orchestrator, store = build_orchestrator()
    now = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    store.modes.save(
        ModeConfig(
            user_id="user-1",
            mode=AgentMode.QUIET,
            started_at=now,
            expires_at=None,
            do_not_disturb_windows=[],
            daily_checkin_windows={},
            tone_preferences={},
            memory_strategy="explicit_only",
        )
    )
    task = ScheduledTask(
        task_id="task-quiet-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        task_type=TaskType.MORNING_CHECKIN,
        status=TaskStatus.PENDING,
        trigger_at=now,
        payload={"goal": "collect_sleep_and_mood"},
        source_message_id=None,
    )
    store.tasks.save(task)

    outgoing = orchestrator.handle_scheduled_task(task, now=now)
    due = store.tasks.list_due("user-1", now.isoformat())

    assert outgoing.content == ""
    assert outgoing.metadata["suppressed"] is True
    assert outgoing.metadata["reason"] == "quiet_mode_blocks_routine_checkin"
    assert due == []


def test_quiet_mode_inbound_text_reply_uses_gentle_tone():
    orchestrator, store = build_orchestrator()
    now = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    store.modes.save(
        ModeConfig(
            user_id="user-1",
            mode=AgentMode.QUIET,
            started_at=now,
            expires_at=None,
            do_not_disturb_windows=[],
            daily_checkin_windows={},
            tone_preferences={},
            memory_strategy="explicit_only",
        )
    )
    message = NormalizedMessage(
        message_id="msg-quiet-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I am overwhelmed today.",
        media_ref=None,
        timestamp=now,
        metadata={},
    )

    reply = orchestrator.handle_message(message)

    assert reply.content == "I am here. We can go slowly."


def test_coach_mode_inbound_image_reply_uses_encouraging_tone():
    orchestrator, store = build_orchestrator()
    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    store.modes.save(
        ModeConfig(
            user_id="user-1",
            mode=AgentMode.COACH,
            started_at=now,
            expires_at=None,
            do_not_disturb_windows=[],
            daily_checkin_windows={},
            tone_preferences={},
            memory_strategy="active_tracking",
        )
    )
    message = NormalizedMessage(
        message_id="msg-coach-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.IMAGE,
        content=None,
        media_ref="meal.jpg",
        timestamp=now,
        metadata={},
    )

    reply = orchestrator.handle_message(message)

    assert reply.content == "Nice. I will save this as an estimate so we can keep tracking."
