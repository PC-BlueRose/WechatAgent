from __future__ import annotations

from wechat_agent.llm.gateway import (
    ChatRequest,
    ChatResponse,
    EmbeddingResult,
    ExtractedEvent,
    ExtractionResult,
    ImageAnalysisResult,
)


class FakeLLMGateway:
    def chat(self, request: ChatRequest) -> ChatResponse:
        if request.intent == "morning_checkin":
            return ChatResponse(content="Morning. How did you sleep last night? Any dreams?")
        if request.intent == "food_photo_response":
            return ChatResponse(
                content="I will save this as an estimate, not a precise measurement."
            )
        if request.intent == "reminder_confirmation":
            return ChatResponse(content="Got it. I will remind you when it is time.")
        return ChatResponse(content="I am here. Take your time.")

    def extract_life_events(
        self, user_id: str, source_message_id: str, text: str
    ) -> ExtractionResult:
        lowered = text.lower()
        events: list[ExtractedEvent] = []
        if "slept" in lowered or "sleep" in lowered:
            events.append(
                ExtractedEvent(
                    event_type="sleep",
                    payload={"sleep_time": "02:00", "waking_state": "tired"},
                    confidence=0.8,
                    is_estimate=True,
                )
            )
        if "remind" in lowered:
            events.append(
                ExtractedEvent(
                    event_type="reminder",
                    payload={"content": text, "time_text": "tomorrow morning"},
                    confidence=0.7,
                    is_estimate=True,
                )
            )
        return ExtractionResult(events=events)

    def analyze_food_image(self, user_id: str, media_ref: str) -> ImageAnalysisResult:
        return ImageAnalysisResult(
            payload={
                "foods": ["rice", "chicken", "vegetables"],
                "estimated_calories_range": [550, 750],
                "protein": "medium",
                "carbs": "medium_high",
                "fat": "medium",
            },
            confidence=0.65,
            is_estimate=True,
        )

    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(embedding=[float(min(len(text), 100)) / 100.0, 0.0, 1.0])
