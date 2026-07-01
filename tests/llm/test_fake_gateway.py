from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.llm.gateway import ChatRequest


def test_fake_gateway_extracts_sleep_event_from_text():
    gateway = FakeLLMGateway()

    result = gateway.extract_life_events(
        user_id="user-1",
        source_message_id="msg-1",
        text="I slept around 2 and woke up tired.",
    )

    assert result.events[0].event_type == "sleep"
    assert result.events[0].payload["sleep_time"] == "02:00"
    assert result.events[0].confidence == 0.8


def test_fake_gateway_returns_uncertain_food_analysis():
    gateway = FakeLLMGateway()

    result = gateway.analyze_food_image(user_id="user-1", media_ref="meal.jpg")

    assert result.is_estimate is True
    assert "estimated_calories_range" in result.payload


def test_fake_gateway_chat_uses_tone_and_intent():
    gateway = FakeLLMGateway()
    response = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="morning_checkin",
            tone="warm_daily",
            user_text=None,
            memories=[],
            recent_messages=[],
            facts={"goal": "collect_sleep_and_mood"},
        )
    )

    assert "How did you sleep last night" in response.content


def test_fake_gateway_chat_varies_by_tone_for_same_intent():
    gateway = FakeLLMGateway()

    gentle = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="morning_checkin",
            tone="gentle",
            user_text=None,
            memories=[],
            recent_messages=[],
            facts={},
        )
    )
    warm_daily = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="morning_checkin",
            tone="warm_daily",
            user_text=None,
            memories=[],
            recent_messages=[],
            facts={},
        )
    )
    encouraging = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="morning_checkin",
            tone="encouraging",
            user_text=None,
            memories=[],
            recent_messages=[],
            facts={},
        )
    )

    assert gentle.content == "Hey. How did you sleep last night?"
    assert warm_daily.content == "Morning. How did you sleep last night? Any dreams?"
    assert encouraging.content == "Good morning. How did you sleep last night? Let's build on today."


def test_fake_gateway_user_reminder_chat_uses_payload_content():
    gateway = FakeLLMGateway()

    response = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="user_reminder",
            tone="gentle",
            user_text=None,
            memories=[],
            recent_messages=[],
            facts={"content": "Take your vitamins."},
        )
    )

    assert response.content == "Reminder: Take your vitamins."


def test_fake_gateway_extracts_reminder_event_from_text():
    gateway = FakeLLMGateway()

    result = gateway.extract_life_events(
        user_id="user-1",
        source_message_id="msg-2",
        text="Remind me tomorrow morning to stretch.",
    )

    assert len(result.events) == 1
    assert result.events[0].event_type == "reminder"
    assert result.events[0].payload == {
        "content": "Remind me tomorrow morning to stretch.",
        "time_text": "tomorrow morning",
    }
    assert result.events[0].confidence == 0.7
    assert result.events[0].is_estimate is True


def test_fake_gateway_embed_is_deterministic():
    gateway = FakeLLMGateway()

    short = gateway.embed("hello")
    long = gateway.embed("x" * 120)

    assert short.embedding == [0.05, 0.0, 1.0]
    assert long.embedding == [1.0, 0.0, 1.0]
