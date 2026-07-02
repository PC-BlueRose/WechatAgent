import pytest


@pytest.fixture(autouse=True)
def cli_dotenv(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "WECHAT_AGENT_LLM_PROVIDER=fake",
                "WECHAT_AGENT_MINIMAX_BASE_URL=https://api.minimax.io/v1",
                "WECHAT_AGENT_MINIMAX_CHAT_MODEL=MiniMax-M3",
                "WECHAT_AGENT_MINIMAX_EXTRACTION_MODEL=MiniMax-M3",
                "WECHAT_AGENT_MINIMAX_EMBEDDING_MODEL=MiniMax-Embedding-01",
                "WECHAT_AGENT_MINIMAX_TIMEOUT_SECONDS=30",
                "WECHAT_AGENT_MINIMAX_USE_FAKE_VISION_FALLBACK=true",
                "WECHAT_AGENT_STORAGE_BACKEND=inmemory",
                "WECHAT_AGENT_DB_HOST=127.0.0.1",
                "WECHAT_AGENT_DB_PORT=5432",
                "WECHAT_AGENT_DB_NAME=wechat_agent",
                "WECHAT_AGENT_DB_USER=postgres",
                "WECHAT_AGENT_DB_PASSWORD=",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return dotenv
