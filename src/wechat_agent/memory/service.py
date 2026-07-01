from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.messages import MessageType, NormalizedMessage
from wechat_agent.llm.gateway import LLMGateway
from wechat_agent.storage.in_memory import InMemoryStore


class MemoryService:
    def __init__(self, store: InMemoryStore, llm: LLMGateway) -> None:
        self._store = store
        self._llm = llm
        self._memory_owners: dict[str, str] = {}

    def save_raw_message(self, message: NormalizedMessage) -> None:
        self._store.messages.save(message)

    def extract_and_store(self, message: NormalizedMessage) -> list[LifeEvent]:
        self.save_raw_message(message)
        if message.message_type is not MessageType.TEXT or not message.content:
            return []

        result = self._llm.extract_life_events(
            user_id=message.user_id,
            source_message_id=message.message_id,
            text=message.content,
        )

        events: list[LifeEvent] = []
        recorded_at = datetime.now(UTC)
        for extracted in result.events:
            event = LifeEvent(
                event_id=f"event-{uuid4()}",
                user_id=message.user_id,
                event_type=LifeEventType(extracted.event_type),
                occurred_at=message.timestamp,
                recorded_at=recorded_at,
                source_message_id=message.message_id,
                confidence=extracted.confidence,
                payload=extracted.payload,
                is_estimate=extracted.is_estimate,
                confirmation_status="unconfirmed",
            )
            self._store.life_events.save(event)
            events.append(event)
        return events

    def remember_candidate(
        self, user_id: str, category: str, content: str, source_ref: str
    ) -> LongTermMemory:
        timestamp = datetime.now(UTC)
        memory = LongTermMemory(
            memory_id=f"mem-{uuid4()}",
            user_id=user_id,
            category=category,
            content=content,
            importance=0.7,
            confidence=0.8,
            source_ref=source_ref,
            created_at=timestamp,
            updated_at=timestamp,
            state=MemoryState.ACTIVE,
            embedding=self._llm.embed(content).embedding,
        )
        self._store.memories.save(memory)
        self._memory_owners[memory.memory_id] = user_id
        return memory

    def recall(self, user_id: str, query: str, limit: int = 5) -> list[LongTermMemory]:
        query_embedding = self._llm.embed(query).embedding
        memories = self._store.memories.list_active(user_id)
        for memory in memories:
            self._memory_owners[memory.memory_id] = memory.user_id
        ranked = sorted(
            memories,
            key=lambda memory: (
                self._embedding_distance(memory.embedding, query_embedding),
                memory.created_at,
            ),
        )
        return ranked[:limit]

    def forget_memory(self, memory_id: str) -> None:
        user_id = self._memory_owners.get(memory_id)
        if user_id is None:
            return
        memory = next(
            (
                active_memory
                for active_memory in self._store.memories.list_active(user_id)
                if active_memory.memory_id == memory_id
            ),
            None,
        )
        if memory is None:
            return

        self._store.memories.replace(
            memory.model_copy(
                update={
                    "state": MemoryState.DENIED,
                    "updated_at": datetime.now(UTC),
                }
            )
        )

    @staticmethod
    def _embedding_distance(
        memory_embedding: list[float] | None, query_embedding: list[float]
    ) -> float:
        if memory_embedding is None:
            return float("inf")
        if len(memory_embedding) != len(query_embedding):
            raise ValueError(
                "Embedding dimension mismatch: "
                f"memory={len(memory_embedding)} query={len(query_embedding)}"
            )

        return sum(
            abs(memory_value - query_value)
            for memory_value, query_value in zip(memory_embedding, query_embedding)
        )
