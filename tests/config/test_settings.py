from wechat_agent.config import load_settings


def test_load_settings_defaults_to_fake_provider(monkeypatch):
    monkeypatch.delenv("WECHAT_AGENT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("WECHAT_AGENT_MINIMAX_API_KEY", raising=False)

    settings = load_settings()

    assert settings.llm_provider == "fake"
    assert settings.minimax.api_key is None
    assert settings.minimax.timeout_seconds == 30
    assert settings.minimax.use_fake_vision_fallback is True


def test_load_settings_reads_minimax_models(monkeypatch):
    monkeypatch.setenv("WECHAT_AGENT_LLM_PROVIDER", "minimax")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_API_KEY", "test-key")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_BASE_URL", "https://api.minimax.chat")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_CHAT_MODEL", "chat-model")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL", "extract-model")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL", "embed-model")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_VISION_MODEL", "vision-model")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK", "false")

    settings = load_settings()

    assert settings.llm_provider == "minimax"
    assert settings.minimax.api_key == "test-key"
    assert settings.minimax.base_url == "https://api.minimax.chat"
    assert settings.minimax.chat_model == "chat-model"
    assert settings.minimax.extraction_model == "extract-model"
    assert settings.minimax.embedding_model == "embed-model"
    assert settings.minimax.vision_model == "vision-model"
    assert settings.minimax.timeout_seconds == 45
    assert settings.minimax.use_fake_vision_fallback is False


def test_load_settings_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("WECHAT_AGENT_LLM_PROVIDER", "other")

    try:
        load_settings()
    except ValueError as exc:
        assert "Unsupported LLM provider" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for unsupported provider")
