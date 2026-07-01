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
    def _tone_variant(self, tone: str, variants: dict[str, str], default: str) -> str:
        return variants.get(tone, default)

    def chat(self, request: ChatRequest) -> ChatResponse:
        if request.intent == "morning_checkin":
            return ChatResponse(
                content=self._tone_variant(
                    request.tone,
                    {
                        "gentle": "Hey. How did you sleep last night?",
                        "warm_daily": "Morning. How did you sleep last night? Any dreams?",
                        "encouraging": (
                            "Good morning. How did you sleep last night? "
                            "Let's build on today."
                        ),
                    },
                    "Morning. How did you sleep last night? Any dreams?",
                )
            )
        if request.intent == "food_photo_response":
            return ChatResponse(
                content=self._tone_variant(
                    request.tone,
                    {
                        "gentle": "I will save this as an estimate.",
                        "warm_daily": (
                            "I will save this as an estimate, not a precise measurement."
                        ),
                        "encouraging": (
                            "Nice. I will save this as an estimate so we can keep tracking."
                        ),
                    },
                    "I will save this as an estimate, not a precise measurement.",
                )
            )
        if request.intent == "reminder_confirmation":
            return ChatResponse(
                content=self._tone_variant(
                    request.tone,
                    {
                        "gentle": "Okay. I will remind you when it is time.",
                        "warm_daily": "Got it. I will remind you when it is time.",
                        "encouraging": "Got it. I will remind you and help you follow through.",
                    },
                    "Got it. I will remind you when it is time.",
                )
            )
        if request.intent == "user_reminder":
            reminder = str(request.facts.get("content", "")).strip()
            content = reminder or "It is time."
            return ChatResponse(
                content=self._tone_variant(
                    request.tone,
                    {
                        "gentle": f"Reminder: {content}",
                        "warm_daily": f"Reminder: {content}",
                        "encouraging": f"Reminder: {content}",
                    },
                    f"Reminder: {content}",
                )
            )
        return ChatResponse(
            content=self._tone_variant(
                request.tone,
                {
                    "gentle": "I am here. We can go slowly.",
                    "warm_daily": "I am here. Take your time.",
                    "encouraging": "I am here. We can take the next step together.",
                },
                "I am here. Take your time.",
            )
        )

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
