from datetime import UTC, date, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.channels.test_channel import TestChannelAdapter
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def test_e2e_daily_checkin_sleep_reply_and_food_photo_flow():
    store = InMemoryStore()
    llm = FakeLLMGateway()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    orchestrator = AgentOrchestrator(store, llm, memory, scheduler, policy)
    channel = TestChannelAdapter(orchestrator=orchestrator)

    scheduler.create_daily_checkins("user-1", "conv-1", "test", date(2026, 7, 1))
    due = scheduler.due_allowed_tasks("user-1", datetime(2026, 7, 1, 8, 1, tzinfo=UTC))
    morning = orchestrator.handle_scheduled_task(
        due[0], now=datetime(2026, 7, 1, 8, 1, tzinfo=UTC)
    )
    channel.send(morning)

    channel.receive_text(
        user_id="user-1",
        conversation_id="conv-1",
        content="I slept around 2 and woke up tired.",
        timestamp=datetime(2026, 7, 1, 8, 5, tzinfo=UTC),
    )
    channel.receive_image(
        user_id="user-1",
        conversation_id="conv-1",
        media_ref="meal.jpg",
        timestamp=datetime(2026, 7, 1, 12, 40, tzinfo=UTC),
    )

    event_types = [event.event_type.value for event in store.life_events.list_for_user("user-1")]
    assert event_types == ["sleep", "meal"]
    assert len(channel.sent_messages) == 3
