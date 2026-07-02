from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.channels.test_channel import TestChannelAdapter
from wechat_agent.config import load_settings
from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.llm.minimax_gateway import MiniMaxLLMGateway
from wechat_agent.memory.service import MemoryService
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.scheduler.service import SchedulerService
from wechat_agent.storage.factory import build_store
from wechat_agent.storage.store import Store


CHECKIN_TASKS: dict[str, TaskType] = {
    "morning": TaskType.MORNING_CHECKIN,
    "lunch": TaskType.LUNCH_MEAL_CHECKIN,
    "afternoon": TaskType.AFTERNOON_ENERGY_CHECKIN,
    "evening": TaskType.EVENING_REVIEW,
    "bedtime": TaskType.BEDTIME_WINDDOWN,
}

SUPPRESSED_CHECKIN_MESSAGES: dict[str, str] = {
    "quiet_mode_blocks_routine_checkin": (
        "Check-in suppressed: quiet mode blocks routine check-ins."
    ),
}


def _build_llm() -> FakeLLMGateway | MiniMaxLLMGateway:
    settings = load_settings()
    if settings.llm_provider == "minimax":
        return MiniMaxLLMGateway(settings=settings.minimax)
    return FakeLLMGateway()


@dataclass
class CliSession:
    store: Store
    orchestrator: AgentOrchestrator
    scheduler: SchedulerService
    policy: PolicyEngine
    channel: TestChannelAdapter
    user_id: str
    conversation_id: str
    channel_name: str

    def handle_text(self, text: str, now: datetime | None = None) -> str:
        timestamp = now or datetime.now(UTC)
        reply = self.channel.receive_text(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            content=text,
            timestamp=timestamp,
        )
        return reply.content

    def set_mode(self, mode: AgentMode, now: datetime | None = None) -> None:
        timestamp = now or datetime.now(UTC)
        self.store.modes.save(
            ModeConfig(
                user_id=self.user_id,
                mode=mode,
                started_at=timestamp,
                expires_at=None,
                do_not_disturb_windows=[],
                daily_checkin_windows={},
                tone_preferences={},
                memory_strategy="cli_manual",
            )
        )

    def send_checkin(self, checkin_name: str, now: datetime | None = None) -> str:
        timestamp = now or datetime.now(UTC)
        task = ScheduledTask(
            task_id=f"cli-{checkin_name}-{int(timestamp.timestamp())}",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            channel=self.channel_name,
            task_type=CHECKIN_TASKS[checkin_name],
            status=TaskStatus.PENDING,
            trigger_at=timestamp,
            payload={"goal": checkin_name},
            source_message_id=None,
        )
        reply = self.orchestrator.handle_scheduled_task(task, now=timestamp)
        if reply.metadata.get("suppressed"):
            reason = str(reply.metadata.get("reason", "")).strip()
            return SUPPRESSED_CHECKIN_MESSAGES.get(
                reason, "Check-in suppressed by policy."
            )
        if reply.content:
            self.channel.send(reply)
        return reply.content

    def send_due_tasks(self, now: datetime | None = None) -> list[str]:
        timestamp = now or datetime.now(UTC)
        outputs: list[str] = []
        for task in self.scheduler.due_allowed_tasks(self.user_id, timestamp):
            reply = self.orchestrator.handle_scheduled_task(task, now=timestamp)
            if reply.content:
                self.channel.send(reply)
                outputs.append(reply.content)
        return outputs

    def format_state(self, now: datetime | None = None) -> str:
        timestamp = now or datetime.now(UTC)
        mode = self.policy.get_effective_mode(self.user_id, timestamp).value
        recent_events = self.store.life_events.list_for_user(self.user_id)[-5:]
        active_memories = self.store.memories.list_active(self.user_id)
        task_counts = self.store.tasks.status_counts(self.user_id)

        if recent_events:
            event_lines = [
                f"- {event.event_type.value} @ {event.occurred_at.isoformat()}"
                for event in recent_events
            ]
        else:
            event_lines = ["- none"]

        task_summary = ", ".join(
            f"{status}={count}" for status, count in sorted(task_counts.items())
        ) or "none"
        return "\n".join(
            [
                f"Mode: {mode}",
                f"Active memories: {len(active_memories)}",
                f"Tasks: {task_summary}",
                "Recent events:",
                *event_lines,
            ]
        )


def build_cli_session() -> CliSession:
    settings = load_settings()
    store = build_store(settings.database)
    llm = _build_llm()
    policy = PolicyEngine(store.modes)
    memory = MemoryService(store=store, llm=llm)
    scheduler = SchedulerService(store=store, policy=policy)
    orchestrator = AgentOrchestrator(store, llm, memory, scheduler, policy)
    channel = TestChannelAdapter(orchestrator=orchestrator)
    return CliSession(
        store=store,
        orchestrator=orchestrator,
        scheduler=scheduler,
        policy=policy,
        channel=channel,
        user_id="cli-user",
        conversation_id="cli-conversation",
        channel_name="test",
    )
