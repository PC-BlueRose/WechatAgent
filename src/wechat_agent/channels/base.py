from __future__ import annotations

from typing import Protocol

from wechat_agent.domain.messages import NormalizedMessage, OutgoingMessage


class ChannelAdapter(Protocol):
    def normalize(self, raw: dict[str, object]) -> NormalizedMessage: ...
    def send(self, message: OutgoingMessage) -> None: ...
