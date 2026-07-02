from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LLMProvider = Literal["fake", "minimax"]
StorageBackend = Literal["inmemory", "postgres"]


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
class DatabaseSettings:
    backend: StorageBackend
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass(frozen=True)
class AppSettings:
    llm_provider: LLMProvider
    minimax: MiniMaxSettings
    database: DatabaseSettings


def _project_root() -> Path:
    return Path.cwd()


def _parse_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ValueError(f"Missing .env file at project root: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        values[key.strip()] = value.strip()
    return values


def _read_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, raw: str | None, default: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def _require(name: str, values: dict[str, str]) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required config: {name}")
    return value


def load_settings(dotenv_path: str | None = None) -> AppSettings:
    path = Path(dotenv_path) if dotenv_path is not None else _project_root() / ".env"
    values = _parse_dotenv(path)

    provider_raw = values.get("WECHAT_AGENT_LLM_PROVIDER", "fake").strip().lower()
    if provider_raw not in {"fake", "minimax"}:
        raise ValueError(f"Unsupported LLM provider: {provider_raw}")

    database = DatabaseSettings(
        backend=values.get("WECHAT_AGENT_STORAGE_BACKEND", "postgres").strip().lower(),  # type: ignore[arg-type]
        host=values.get("WECHAT_AGENT_DB_HOST", "127.0.0.1"),
        port=_read_int("WECHAT_AGENT_DB_PORT", values.get("WECHAT_AGENT_DB_PORT"), 5432),
        name=values.get("WECHAT_AGENT_DB_NAME", "wechat_agent"),
        user=values.get("WECHAT_AGENT_DB_USER", "postgres"),
        password=values.get("WECHAT_AGENT_DB_PASSWORD", ""),
    )
    if database.backend not in {"inmemory", "postgres"}:
        raise ValueError(f"Unsupported storage backend: {database.backend}")

    if provider_raw == "fake":
        return AppSettings(
            llm_provider="fake",
            minimax=MiniMaxSettings(
                api_key=None,
                base_url=values.get(
                    "WECHAT_AGENT_MINIMAX_BASE_URL", "https://api.minimax.io/v1"
                ),
                chat_model=values.get("WECHAT_AGENT_MINIMAX_CHAT_MODEL", "MiniMax-M3"),
                extraction_model=values.get(
                    "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL", "MiniMax-M3"
                ),
                embedding_model=values.get(
                    "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL", "MiniMax-Embedding-01"
                ),
                vision_model=values.get("WECHAT_AGENT_MINIMAX_VISION_MODEL") or None,
                timeout_seconds=_read_int(
                    "WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS",
                    values.get("WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS"),
                    30,
                ),
                use_fake_vision_fallback=_read_bool(
                    values.get("WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK"), True
                ),
            ),
            database=database,
        )

    minimax = MiniMaxSettings(
        api_key=_require("WECHAT_AGENT_MINIMAX_API_KEY", values),
        base_url=_require("WECHAT_AGENT_MINIMAX_BASE_URL", values),
        chat_model=_require("WECHAT_AGENT_MINIMAX_CHAT_MODEL", values),
        extraction_model=_require("WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL", values),
        embedding_model=_require("WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL", values),
        vision_model=values.get("WECHAT_AGENT_MINIMAX_VISION_MODEL") or None,
        timeout_seconds=_read_int(
            "WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS",
            values.get("WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS"),
            30,
        ),
        use_fake_vision_fallback=_read_bool(
            values.get("WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK"), True
        ),
    )
    return AppSettings(llm_provider="minimax", minimax=minimax, database=database)
