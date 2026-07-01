from datetime import UTC, datetime, timedelta

from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import TaskType
from wechat_agent.policy.engine import PolicyEngine
from wechat_agent.storage.in_memory import InMemoryStore


def test_expired_quiet_mode_falls_back_to_daily():
    store = InMemoryStore()
    now = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    store.modes.save(
        ModeConfig(
            user_id="user-1",
            mode=AgentMode.QUIET,
            started_at=now - timedelta(days=1),
            expires_at=now - timedelta(minutes=1),
            do_not_disturb_windows=[],
            daily_checkin_windows={},
            tone_preferences={},
            memory_strategy="explicit_only",
        )
    )

    engine = PolicyEngine(store.modes)

    assert engine.get_effective_mode("user-1", now) is AgentMode.DAILY


def test_quiet_mode_blocks_lunch_checkin_but_allows_user_reminder():
    store = InMemoryStore()
    now = datetime(2026, 7, 1, 12, 30, tzinfo=UTC)
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
    engine = PolicyEngine(store.modes)

    lunch = engine.evaluate_checkin("user-1", TaskType.LUNCH_MEAL_CHECKIN, now)
    reminder = engine.evaluate_checkin("user-1", TaskType.USER_REMINDER, now)

    assert lunch.allowed is False
    assert lunch.reason == "quiet_mode_blocks_routine_checkin"
    assert reminder.allowed is True
    assert reminder.tone == "gentle"
