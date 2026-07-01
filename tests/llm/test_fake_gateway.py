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
