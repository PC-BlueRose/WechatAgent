from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.messages import MessageType, NormalizedMessage, OutgoingMessage
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.llm.gateway import ChatRequest, LLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.store import Store


class AgentOrchestrator:
    def __init__(
        self,
        store: Store,
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
        tone = self._policy.response_tone(message.user_id, message.timestamp)
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
                    tone=tone,
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
        reminder_events = [
            event for event in events if event.event_type is LifeEventType.REMINDER
        ]
        for event in reminder_events:
            self._scheduler.create_user_reminder(
                user_id=message.user_id,
                conversation_id=message.conversation_id,
                channel=message.channel,
                trigger_at=self._resolve_reminder_trigger_at(message.timestamp, event),
                content=str(event.payload.get("content", message.content or "")),
                source_message_id=message.message_id,
            )
        intent = (
            "reminder_confirmation"
            if reminder_events
            else "chat"
        )
        response = self._llm.chat(
            ChatRequest(
                user_id=message.user_id,
                intent=intent,
                tone=tone,
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
        if not decision.allowed:
            self._mark_task_status(task, TaskStatus.EXPIRED)
            return OutgoingMessage(
                conversation_id=task.conversation_id,
                channel=task.channel,
                content="",
                metadata={
                    "task_id": task.task_id,
                    "intent": task.task_type.value,
                    "suppressed": True,
                    "reason": decision.reason,
                },
            )

        if task.task_type is TaskType.USER_REMINDER:
            self._mark_task_status(task, TaskStatus.SENT)
            return OutgoingMessage(
                conversation_id=task.conversation_id,
                channel=task.channel,
                content=str(task.payload.get("content", "")).strip(),
                metadata={"task_id": task.task_id, "intent": task.task_type.value},
            )

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
        self._mark_task_status(task, TaskStatus.SENT)
        return OutgoingMessage(
            conversation_id=task.conversation_id,
            channel=task.channel,
            content=response.content,
            metadata={"task_id": task.task_id, "intent": task.task_type.value},
        )

    def _mark_task_status(self, task: ScheduledTask, status: TaskStatus) -> None:
        try:
            self._store.tasks.update_status(task.task_id, status)
        except KeyError:
            self._store.tasks.save(task.model_copy(update={"status": status}))

    @staticmethod
    def _resolve_reminder_trigger_at(
        message_timestamp: datetime, event: LifeEvent
    ) -> datetime:
        time_text = str(event.payload.get("time_text", "")).strip().lower()
        tzinfo = message_timestamp.tzinfo or UTC
        if time_text == "tomorrow morning":
            return datetime.combine(
                message_timestamp.date() + timedelta(days=1),
                time(8, 0),
                tzinfo=tzinfo,
            )
        return message_timestamp
