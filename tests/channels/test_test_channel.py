from datetime import UTC, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.channels.test_channel import TestChannelAdapter
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


def build_channel():
    store = InMemoryStore()
    llm = FakeLLMGateway()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    orchestrator = AgentOrchestrator(store, llm, memory, scheduler, policy)
    return TestChannelAdapter(orchestrator=orchestrator), store


def test_test_channel_receives_text_and_sends_reply():
    channel, store = build_channel()

    reply = channel.receive_text(
        user_id="user-1",
        conversation_id="conv-1",
        content="I slept around 2.",
        timestamp=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
    )

    assert reply in channel.sent_messages
    assert len(store.life_events.list_for_user("user-1")) == 1
