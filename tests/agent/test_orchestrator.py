from datetime import UTC, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
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
