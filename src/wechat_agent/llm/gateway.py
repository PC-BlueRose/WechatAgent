from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str
    intent: str
    tone: str
    user_text: str | None
    memories: list[str] = Field(default_factory=list)
    recent_messages: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    content: str
    used_memory_ids: list[str] = Field(default_factory=list)
    risk_level: str = "normal"


class ExtractedEvent(BaseModel):
    event_type: str
    payload: dict[str, Any]
    confidence: float
    is_estimate: bool


class ExtractionResult(BaseModel):
    events: list[ExtractedEvent]
    long_term_memory_candidates: list[str] = Field(default_factory=list)
    needs_follow_up: bool = False
    follow_up_question: str | None = None


class ImageAnalysisResult(BaseModel):
    payload: dict[str, Any]
    confidence: float
    is_estimate: bool


class EmbeddingResult(BaseModel):
    embedding: list[float]


class LLMGateway(Protocol):
    def chat(self, request: ChatRequest) -> ChatResponse: ...

    def extract_life_events(
        self, user_id: str, source_message_id: str, text: str
    ) -> ExtractionResult: ...

    def analyze_food_image(self, user_id: str, media_ref: str) -> ImageAnalysisResult: ...

    def embed(self, text: str) -> EmbeddingResult: ...
