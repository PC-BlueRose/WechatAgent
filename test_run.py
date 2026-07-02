from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wechat_agent.cli.app import main as cli_main
from wechat_agent.config import AppSettings, load_settings


def _format_startup_message(settings: AppSettings) -> str:
    provider = settings.llm_provider
    if provider == "minimax":
        return (
            "Config OK. "
            f"Provider={provider}, "
            f"chat_model={settings.minimax.chat_model}, "
            f"storage={settings.database.backend}, "
            f"db={settings.database.host}:{settings.database.port}/{settings.database.name}"
        )
    return (
        "Config OK. "
        f"Provider={provider}, "
        f"storage={settings.database.backend}, "
        f"db={settings.database.host}:{settings.database.port}/{settings.database.name}"
    )


def main() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"Config error: {exc}")
        return 1

    print(_format_startup_message(settings))
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
