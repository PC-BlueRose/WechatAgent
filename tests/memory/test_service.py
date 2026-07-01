from datetime import UTC, datetime

from wechat_agent.domain.events import LifeEventType
from wechat_agent.domain.memory import MemoryState
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.storage.in_memory import InMemoryStore


def test_memory_service_saves_raw_message_before_extracted_event():
    store = InMemoryStore()
    service = MemoryService(store=store, llm=FakeLLMGateway())
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

    events = service.extract_and_store(message)

    assert store.messages.get("msg-1") == message
    assert len(events) == 1
    assert events[0].event_type is LifeEventType.SLEEP
    assert store.life_events.list_for_user("user-1")[0].source_message_id == "msg-1"


def test_memory_service_remembers_candidate_with_embedding():
    store = InMemoryStore()
    service = MemoryService(store=store, llm=FakeLLMGateway())

    memory = service.remember_candidate(
        user_id="user-1",
        category="preference",
        content="User prefers gentle reminders.",
        source_ref="msg-1",
    )

    active = store.memories.list_active("user-1")

    assert active == [memory]
    assert memory.state is MemoryState.ACTIVE
    assert memory.embedding == [0.3, 0.0, 1.0]


def test_memory_service_recalls_active_memories_using_embedding_similarity():
    store = InMemoryStore()
    service = MemoryService(store=store, llm=FakeLLMGateway())
    near = service.remember_candidate(
        user_id="user-1",
        category="plan",
        content="stretch plan",
        source_ref="msg-1",
    )
    mid = service.remember_candidate(
        user_id="user-1",
        category="plan",
        content="longer stretching routine",
        source_ref="msg-2",
    )
    far = service.remember_candidate(
        user_id="user-1",
        category="plan",
        content="very long stretching routine for weekends",
        source_ref="msg-3",
    )

    recalled = service.recall(user_id="user-1", query="stretch now", limit=2)

    assert recalled == [near, mid]
    assert far not in recalled


def test_forget_memory_marks_memory_denied():
    store = InMemoryStore()
    service = MemoryService(store=store, llm=FakeLLMGateway())
    memory = service.remember_candidate(
        user_id="user-1",
        category="preference",
        content="User prefers gentle reminders.",
        source_ref="msg-1",
    )

    service.forget_memory(memory.memory_id)

    assert store.memories.list_active("user-1") == []
    denied_memory = store.memories._memories[memory.memory_id]
    assert denied_memory.state is MemoryState.DENIED
