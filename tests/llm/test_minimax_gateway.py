from wechat_agent.config import MiniMaxSettings
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.llm.gateway import ChatRequest
from wechat_agent.llm.minimax_gateway import MiniMaxLLMGateway


class StubMiniMaxGateway(MiniMaxLLMGateway):
    def __init__(self, settings: MiniMaxSettings, responses: list[dict], fallback=None):
        super().__init__(settings=settings, fallback=fallback)
        self._responses = list(responses)
        self.requests: list[dict] = []

    def _post_json(self, path: str, payload: dict) -> dict:
        self.requests.append({"path": path, "payload": payload})
        return self._responses.pop(0)


def build_settings(
    *,
    vision_model: str | None = None,
    use_fake_vision_fallback: bool = True,
) -> MiniMaxSettings:
    return MiniMaxSettings(
        api_key="test-key",
        base_url="https://api.minimax.chat",
        chat_model="chat-model",
        extraction_model="extract-model",
        embedding_model="embed-model",
        vision_model=vision_model,
        timeout_seconds=30,
        use_fake_vision_fallback=use_fake_vision_fallback,
    )


def test_chat_uses_chat_model_and_returns_text():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[
            {
                "choices": [
                    {
                        "message": {
                            "content": "I am here. Take your time."
                        }
                    }
                ]
            }
        ],
    )

    response = gateway.chat(
        ChatRequest(
            user_id="user-1",
            intent="chat",
            tone="warm_daily",
            user_text="I slept badly.",
            memories=["User prefers gentle replies."],
            recent_messages=[],
            facts={"event_count": 1},
        )
    )

    assert response.content == "I am here. Take your time."
    assert gateway.requests[0]["payload"]["model"] == "chat-model"


def test_extract_life_events_parses_json_payload():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "{\"events\":[{\"event_type\":\"sleep\","
                                "\"payload\":{\"sleep_time\":\"02:00\"},"
                                "\"confidence\":0.8,\"is_estimate\":true}],"
                                "\"long_term_memory_candidates\":[],"
                                "\"needs_follow_up\":false,"
                                "\"follow_up_question\":null}"
                            )
                        }
                    }
                ]
            }
        ],
    )

    result = gateway.extract_life_events(
        user_id="user-1",
        source_message_id="msg-1",
        text="I slept around 2.",
    )

    assert result.events[0].event_type == "sleep"
    assert result.events[0].payload["sleep_time"] == "02:00"
    assert gateway.requests[0]["payload"]["model"] == "extract-model"


def test_extract_life_events_returns_empty_result_on_malformed_json():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[{"choices": [{"message": {"content": "not json"}}]}],
    )

    result = gateway.extract_life_events(
        user_id="user-1",
        source_message_id="msg-1",
        text="Remind me tomorrow morning to stretch.",
    )

    assert result.events == []
    assert result.long_term_memory_candidates == []
    assert result.needs_follow_up is False


def test_embed_uses_embedding_model():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[{"data": [{"embedding": [0.1, 0.2, 0.3]}]}],
    )

    result = gateway.embed("hello")

    assert result.embedding == [0.1, 0.2, 0.3]
    assert gateway.requests[0]["payload"]["model"] == "embed-model"


def test_analyze_food_image_uses_fake_fallback_when_enabled():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[],
        fallback=FakeLLMGateway(),
    )

    result = gateway.analyze_food_image(user_id="user-1", media_ref="meal.jpg")

    assert result.is_estimate is True
    assert "foods" in result.payload


def test_analyze_food_image_uses_fake_fallback_when_vision_model_is_configured():
    gateway = StubMiniMaxGateway(
        settings=build_settings(vision_model="vision-model"),
        responses=[],
        fallback=FakeLLMGateway(),
    )

    result = gateway.analyze_food_image(user_id="user-1", media_ref="meal.jpg")

    assert result.is_estimate is True
    assert "foods" in result.payload
