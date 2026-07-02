from __future__ import annotations

from pathlib import Path

import test_run
from wechat_agent.config import AppSettings, DatabaseSettings, MiniMaxSettings


def _build_settings(provider: str = "fake") -> AppSettings:
    return AppSettings(
        llm_provider=provider,  # type: ignore[arg-type]
        minimax=MiniMaxSettings(
            api_key="test-key" if provider == "minimax" else None,
            base_url="https://api.minimax.io/v1",
            chat_model="MiniMax-M3",
            extraction_model="MiniMax-M3",
            embedding_model="MiniMax-Embedding-01",
            vision_model=None,
            timeout_seconds=30,
            use_fake_vision_fallback=True,
        ),
        database=DatabaseSettings(
            backend="postgres",
            host="127.0.0.1",
            port=5432,
            name="wechat_agent",
            user="postgres",
            password="secret",
        ),
    )


def test_main_validates_config_and_starts_cli(monkeypatch, capsys):
    monkeypatch.setattr("test_run.load_settings", lambda: _build_settings("minimax"))
    monkeypatch.setattr("test_run.cli_main", lambda: 0)

    exit_code = test_run.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Config OK." in captured.out
    assert "Provider=minimax" in captured.out
    assert "chat_model=MiniMax-M3" in captured.out


def test_main_returns_error_when_config_is_invalid(monkeypatch, capsys):
    def raise_config_error() -> AppSettings:
        raise ValueError("Missing .env file at project root")

    monkeypatch.setattr("test_run.load_settings", raise_config_error)

    exit_code = test_run.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == "Config error: Missing .env file at project root\n"


def test_root_and_src_paths_are_resolved_from_script_location():
    assert test_run.ROOT == Path(__file__).resolve().parents[2]
    assert test_run.SRC == test_run.ROOT / "src"
