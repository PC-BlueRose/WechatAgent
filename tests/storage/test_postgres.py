from __future__ import annotations

import json
from datetime import UTC, datetime

from wechat_agent.storage.postgres import _json_dumps


def test_json_dumps_serializes_datetime_to_isoformat():
    payload = {
        "timestamp": datetime(2026, 7, 3, 10, 30, tzinfo=UTC),
        "nested": {"created_at": datetime(2026, 7, 3, 10, 31, tzinfo=UTC)},
    }

    encoded = _json_dumps(payload)
    decoded = json.loads(encoded)

    assert decoded == {
        "timestamp": "2026-07-03T10:30:00+00:00",
        "nested": {"created_at": "2026-07-03T10:31:00+00:00"},
    }
