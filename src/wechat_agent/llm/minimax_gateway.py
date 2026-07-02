from __future__ import annotations

import json
from urllib import request

from wechat_agent.config import MiniMaxSettings
from wechat_agent.llm.fake_gateway import FakeLLMGateway
from wechat_agent.llm.gateway import (
    ChatRequest,
    ChatResponse,
    EmbeddingResult,
    ExtractedEvent,
    ExtractionResult,
    ImageAnalysisResult,
)


class MiniMaxLLMGateway:
    def __init__(
        self, settings: MiniMaxSettings, fallback: FakeLLMGateway | None = None
    ) -> None:
        self._settings = settings
        self._fallback = fallback or FakeLLMGateway()

    def chat(self, request_data: ChatRequest) -> ChatResponse:
        payload = {
            "model": self._settings.chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a warm personal life assistant. "
                        "Acknowledge emotion before advice. "
                        "Keep replies concise and natural."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "intent": request_data.intent,
                            "tone": request_data.tone,
                            "user_text": request_data.user_text,
                            "memories": request_data.memories,
                            "recent_messages": request_data.recent_messages,
                            "facts": request_data.facts,
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
        }
        data = self._post_json("/chat/completions", payload)
        content = str(data["choices"][0]["message"]["content"])
        return ChatResponse(content=content)

    def extract_life_events(
        self, user_id: str, source_message_id: str, text: str
    ) -> ExtractionResult:
        empty_result = ExtractionResult(events=[])
        payload = {
            "model": self._settings.extraction_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract supported life events from the user text. "
                        "Return only JSON with keys: events, "
                        "long_term_memory_candidates, needs_follow_up, "
                        "follow_up_question. Supported event_type values "
                        "right now are sleep and reminder."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_id": user_id,
                            "source_message_id": source_message_id,
                            "text": text,
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
        }
        try:
            data = self._post_json("/chat/completions", payload)
            raw = str(data["choices"][0]["message"]["content"])
            parsed = json.loads(raw)
            events = [
                ExtractedEvent(
                    event_type=str(item["event_type"]),
                    payload=dict(item.get("payload", {})),
                    confidence=float(item["confidence"]),
                    is_estimate=bool(item["is_estimate"]),
                )
                for item in parsed.get("events", [])
            ]
            return ExtractionResult(
                events=events,
                long_term_memory_candidates=list(
                    parsed.get("long_term_memory_candidates", [])
                ),
                needs_follow_up=bool(parsed.get("needs_follow_up", False)),
                follow_up_question=parsed.get("follow_up_question"),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return empty_result

    def analyze_food_image(self, user_id: str, media_ref: str) -> ImageAnalysisResult:
        if self._settings.use_fake_vision_fallback:
            return self._fallback.analyze_food_image(
                user_id=user_id, media_ref=media_ref
            )
        if self._settings.vision_model:
            raise NotImplementedError(
                "MiniMax vision integration is not implemented yet."
            )
        raise RuntimeError("MiniMax vision model is not configured.")

    def embed(self, text: str) -> EmbeddingResult:
        payload = {
            "model": self._settings.embedding_model,
            "input": text,
        }
        data = self._post_json("/embeddings", payload)
        embedding = [float(value) for value in data["data"][0]["embedding"]]
        return EmbeddingResult(embedding=embedding)

    def _post_json(self, path: str, payload: dict) -> dict:
        if not self._settings.api_key:
            raise RuntimeError("MiniMax API key is required when provider is minimax.")

        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self._settings.base_url.rstrip('/')}{path}"
        req = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=self._settings.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
