from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

LLMProvider = Literal["fake", "minimax"]


@dataclass(frozen=True)
class MiniMaxSettings:
    api_key: str | None
    base_url: str
    chat_model: str
    extraction_model: str
    embedding_model: str
    vision_model: str | None
    timeout_seconds: int
    use_fake_vision_fallback: bool


@dataclass(frozen=True)
class AppSettings:
    llm_provider: LLMProvider
    minimax: MiniMaxSettings


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> AppSettings:
    provider_raw = os.getenv("WECHAT_AGENT_LLM_PROVIDER", "fake").strip().lower()
    if provider_raw not in {"fake", "minimax"}:
        raise ValueError(f"Unsupported LLM provider: {provider_raw}")

    minimax = MiniMaxSettings(
        api_key=os.getenv("WECHAT_AGENT_MINIMAX_API_KEY"),
        base_url=os.getenv("WECHAT_AGENT_MINIMAX_BASE_URL", "https://api.minimax.chat"),
        chat_model=os.getenv("WECHAT_AGENT_MINIMAX_CHAT_MODEL", "MiniMax-Text-01"),
        extraction_model=os.getenv("WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL", "MiniMax-Text-01"),
        embedding_model=os.getenv("WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL", "MiniMax-Embedding-01"),
        vision_model=os.getenv("WECHAT_AGENT_MINIMAX_VISION_MODEL"),
        timeout_seconds=int(os.getenv("WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS", "30")),
        use_fake_vision_fallback=_read_bool(
            "WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK", True
        ),
    )
    return AppSettings(llm_provider=provider_raw, minimax=minimax)
