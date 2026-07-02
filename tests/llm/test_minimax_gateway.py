import json
from dataclasses import replace
from unittest.mock import patch
from urllib.error import HTTPError, URLError

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
        base_url="https://api.minimax.io/v1",
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
    assert gateway.requests[0]["path"] == "/chat/completions"
    assert gateway.requests[0]["payload"]["model"] == "chat-model"
    assert "thinking" not in gateway.requests[0]["payload"]


def test_chat_strips_inline_thinking_content():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<think>quiet internal reasoning</think>\n"
                                "I am here. Take your time."
                            )
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
            memories=[],
            recent_messages=[],
            facts={},
        )
    )

    assert response.content == "I am here. Take your time."


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
    assert gateway.requests[0]["path"] == "/chat/completions"
    assert gateway.requests[0]["payload"]["model"] == "extract-model"
    assert "thinking" not in gateway.requests[0]["payload"]


def test_extract_life_events_parses_json_payload_when_thinking_is_inlined():
    gateway = StubMiniMaxGateway(
        settings=build_settings(),
        responses=[
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<think>internal reasoning</think>\n"
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


def test_extract_life_events_returns_empty_result_on_transport_failure():
    gateway = MiniMaxLLMGateway(
        settings=build_settings(),
        fallback=FakeLLMGateway(),
    )

    with patch(
        "wechat_agent.llm.minimax_gateway.request.urlopen",
        side_effect=URLError("network down"),
    ):
        result = gateway.extract_life_events(
            user_id="user-1",
            source_message_id="msg-1",
            text="I slept around 2.",
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
    assert gateway.requests[0]["path"] == "/embeddings"
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


def test_post_json_builds_request_with_expected_endpoint_headers_timeout_and_body():
    gateway = MiniMaxLLMGateway(
        settings=build_settings(),
        fallback=FakeLLMGateway(),
    )
    response_body = json.dumps({"ok": True}).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return response_body

    with patch("wechat_agent.llm.minimax_gateway.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = FakeResponse()

        result = gateway._post_json(
            "/embeddings", {"input": "hello", "model": "embed-model"}
        )

    assert result == {"ok": True}
    request_arg = mock_urlopen.call_args.args[0]
    timeout_arg = mock_urlopen.call_args.kwargs["timeout"]
    assert request_arg.full_url == "https://api.minimax.io/v1/embeddings"
    assert request_arg.get_method() == "POST"
    assert request_arg.get_header("Authorization") == "Bearer test-key"
    assert request_arg.get_header("Content-type") == "application/json"
    assert timeout_arg == 30
    assert json.loads(request_arg.data.decode("utf-8")) == {
        "input": "hello",
        "model": "embed-model",
    }


def test_post_json_joins_base_url_when_configured_with_trailing_slash():
    gateway = MiniMaxLLMGateway(
        settings=build_settings(),
        fallback=FakeLLMGateway(),
    )
    gateway._settings = replace(gateway._settings, base_url="https://api.minimax.io/v1/")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"{}"

    with patch("wechat_agent.llm.minimax_gateway.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = FakeResponse()

        gateway._post_json("/chat/completions", {"model": "chat-model"})

    request_arg = mock_urlopen.call_args.args[0]
    assert request_arg.full_url == "https://api.minimax.io/v1/chat/completions"


def test_post_json_surfaces_http_error_details():
    gateway = MiniMaxLLMGateway(
        settings=build_settings(),
        fallback=FakeLLMGateway(),
    )
    http_error = HTTPError(
        url="https://api.minimax.io/v1/chat/completions",
        code=400,
        msg="Bad Request",
        hdrs=None,
        fp=None,
    )
    http_error.read = lambda: (
        b'{"error":{"message":"invalid params","http_code":"400"}}'
    )

    with patch(
        "wechat_agent.llm.minimax_gateway.request.urlopen",
        side_effect=http_error,
    ):
        try:
            gateway._post_json("/chat/completions", {"model": "chat-model"})
        except RuntimeError as exc:
            assert "MiniMax API error 400" in str(exc)
            assert "invalid params" in str(exc)
        else:  # pragma: no cover - defensive failure path
            raise AssertionError("Expected RuntimeError")
