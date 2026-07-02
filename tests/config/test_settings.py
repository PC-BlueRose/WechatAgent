import pytest

from wechat_agent.config import load_settings


def test_load_settings_reads_fake_provider_from_dotenv(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "# local config\nWECHAT_AGENT_LLM_PROVIDER=fake\n",
        encoding="utf-8",
    )

    settings = load_settings(dotenv_path=str(dotenv))

    assert settings.llm_provider == "fake"
    assert settings.minimax.api_key is None
    assert settings.minimax.base_url == "https://api.minimax.io/v1"
    assert settings.minimax.chat_model == "MiniMax-M3"
    assert settings.minimax.extraction_model == "MiniMax-M3"
    assert settings.minimax.timeout_seconds == 30
    assert settings.minimax.use_fake_vision_fallback is True
    assert settings.database.backend == "postgres"
    assert settings.database.host == "127.0.0.1"
    assert settings.database.port == 5432


def test_load_settings_reads_minimax_models_from_dotenv(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "WECHAT_AGENT_LLM_PROVIDER=minimax",
                "WECHAT_AGENT_MINIMAX_API_KEY=test-key",
                "WECHAT_AGENT_MINIMAX_BASE_URL=https://api.minimax.io/v1",
                "WECHAT_AGENT_MINIMAX_CHAT_MODEL=chat-model",
                "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL=extract-model",
                "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL=embed-model",
                "WECHAT_AGENT_MINIMAX_VISION_MODEL=vision-model",
                "WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS=45",
                "WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK=false",
                "WECHAT_AGENT_STORAGE_BACKEND=inmemory",
                "WECHAT_AGENT_DB_HOST=10.0.0.1",
                "WECHAT_AGENT_DB_PORT=15432",
                "WECHAT_AGENT_DB_NAME=agent_db",
                "WECHAT_AGENT_DB_USER=agent_user",
                "WECHAT_AGENT_DB_PASSWORD=secret",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(dotenv_path=str(dotenv))

    assert settings.llm_provider == "minimax"
    assert settings.minimax.api_key == "test-key"
    assert settings.minimax.base_url == "https://api.minimax.io/v1"
    assert settings.minimax.chat_model == "chat-model"
    assert settings.minimax.extraction_model == "extract-model"
    assert settings.minimax.embedding_model == "embed-model"
    assert settings.minimax.vision_model == "vision-model"
    assert settings.minimax.timeout_seconds == 45
    assert settings.minimax.use_fake_vision_fallback is False
    assert settings.database.backend == "inmemory"
    assert settings.database.host == "10.0.0.1"
    assert settings.database.port == 15432
    assert settings.database.name == "agent_db"
    assert settings.database.user == "agent_user"
    assert settings.database.password == "secret"


def test_load_settings_raises_when_dotenv_is_missing(tmp_path):
    missing = tmp_path / ".env"

    with pytest.raises(ValueError, match="Missing \\.env file"):
        load_settings(dotenv_path=str(missing))


def test_load_settings_raises_when_minimax_key_is_missing(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "WECHAT_AGENT_LLM_PROVIDER=minimax",
                "WECHAT_AGENT_MINIMAX_BASE_URL=https://api.minimax.io/v1",
                "WECHAT_AGENT_MINIMAX_CHAT_MODEL=chat-model",
                "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL=extract-model",
                "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL=embed-model",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="WECHAT_AGENT_MINIMAX_API_KEY"):
        load_settings(dotenv_path=str(dotenv))


def test_load_settings_raises_on_invalid_timeout(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "WECHAT_AGENT_LLM_PROVIDER=minimax",
                "WECHAT_AGENT_MINIMAX_API_KEY=test-key",
                "WECHAT_AGENT_MINIMAX_BASE_URL=https://api.minimax.io/v1",
                "WECHAT_AGENT_MINIMAX_CHAT_MODEL=chat-model",
                "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL=extract-model",
                "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL=embed-model",
                "WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS=bad",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS"):
        load_settings(dotenv_path=str(dotenv))


def test_load_settings_rejects_unknown_provider(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("WECHAT_AGENT_LLM_PROVIDER=other\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        load_settings(dotenv_path=str(dotenv))


def test_load_settings_rejects_unknown_storage_backend(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("WECHAT_AGENT_STORAGE_BACKEND=other\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported storage backend"):
        load_settings(dotenv_path=str(dotenv))
