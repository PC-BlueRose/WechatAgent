from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.messages import MessageType, NormalizedMessage, OutgoingMessage
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus
from wechat_agent.llm.gateway import ChatRequest, LLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.in_memory import InMemoryStore


class AgentOrchestrator:
    def __init__(
        self,
        store: InMemoryStore,
        llm: LLMGateway,
        memory: MemoryService,
        scheduler: SchedulerService,
        policy: PolicyEngine,
    ) -> None:
        self._store = store
        self._llm = llm
        self._memory = memory
        self._scheduler = scheduler
        self._policy = policy

    def handle_message(self, message: NormalizedMessage) -> OutgoingMessage:
        if message.message_type is MessageType.IMAGE and message.media_ref:
            self._memory.save_raw_message(message)
            analysis = self._llm.analyze_food_image(message.user_id, message.media_ref)
            event = LifeEvent(
                event_id=f"event-{uuid4()}",
                user_id=message.user_id,
                event_type=LifeEventType.MEAL,
                occurred_at=message.timestamp,
                recorded_at=datetime.now(UTC),
                source_message_id=message.message_id,
                confidence=analysis.confidence,
                payload=analysis.payload,
                is_estimate=analysis.is_estimate,
                confirmation_status="unconfirmed",
            )
            self._store.life_events.save(event)
            response = self._llm.chat(
                ChatRequest(
                    user_id=message.user_id,
                    intent="food_photo_response",
                    tone="warm_daily",
                    user_text=None,
                    facts=analysis.payload,
                )
            )
            return OutgoingMessage(
                conversation_id=message.conversation_id,
                channel=message.channel,
                content=response.content,
                metadata={"intent": "food_photo_response"},
            )

        events = self._memory.extract_and_store(message)
        intent = (
            "reminder_confirmation"
            if any(event.event_type is LifeEventType.REMINDER for event in events)
            else "chat"
        )
        response = self._llm.chat(
            ChatRequest(
                user_id=message.user_id,
                intent=intent,
                tone="warm_daily",
                user_text=message.content,
                memories=[
                    memory.content
                    for memory in self._memory.recall(
                        message.user_id, message.content or ""
                    )
                ],
                recent_messages=[],
                facts={"event_count": len(events)},
            )
        )
        return OutgoingMessage(
            conversation_id=message.conversation_id,
            channel=message.channel,
            content=response.content,
            metadata={"intent": intent},
        )

    def handle_scheduled_task(
        self, task: ScheduledTask, now: datetime
    ) -> OutgoingMessage:
        decision = self._policy.evaluate_checkin(task.user_id, task.task_type, now)
        response = self._llm.chat(
            ChatRequest(
                user_id=task.user_id,
                intent=task.task_type.value,
                tone=decision.tone,
                user_text=None,
                memories=[
                    memory.content
                    for memory in self._memory.recall(task.user_id, task.task_type.value)
                ],
                recent_messages=[],
                facts=task.payload,
            )
        )
        try:
            self._store.tasks.update_status(task.task_id, TaskStatus.SENT)
        except KeyError:
            self._store.tasks.save(task.model_copy(update={"status": TaskStatus.SENT}))
        return OutgoingMessage(
            conversation_id=task.conversation_id,
            channel=task.channel,
            content=response.content,
            metadata={"task_id": task.task_id, "intent": task.task_type.value},
        )
