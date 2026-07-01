from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from wechat_agent.agent.orchestrator import AgentOrchestrator
from wechat_agent.domain.messages import (
    MessageDirection,
    MessageType,
    NormalizedMessage,
    OutgoingMessage,
)


class TestChannelAdapter:
    __test__ = False

    def __init__(self, orchestrator: AgentOrchestrator) -> None:
        self._orchestrator = orchestrator
        self.sent_messages: list[OutgoingMessage] = []

    def normalize(self, raw: dict[str, object]) -> NormalizedMessage:
        return NormalizedMessage(
            message_id=str(raw["message_id"]),
            user_id=str(raw["user_id"]),
            conversation_id=str(raw["conversation_id"]),
            channel="test",
            direction=MessageDirection.INBOUND,
            message_type=MessageType(str(raw["message_type"])),
            content=raw.get("content") if isinstance(raw.get("content"), str) else None,
            media_ref=raw.get("media_ref") if isinstance(raw.get("media_ref"), str) else None,
            timestamp=raw["timestamp"],
            metadata={"raw": "test_channel"},
        )

    def send(self, message: OutgoingMessage) -> None:
        self.sent_messages.append(message)

    def receive_text(
        self, user_id: str, conversation_id: str, content: str, timestamp: datetime
    ) -> OutgoingMessage:
        message = self.normalize(
            {
                "message_id": f"msg-{uuid4()}",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_type": "text",
                "content": content,
                "timestamp": timestamp,
            }
        )
        reply = self._orchestrator.handle_message(message)
        self.send(reply)
        return reply

    def receive_image(
        self, user_id: str, conversation_id: str, media_ref: str, timestamp: datetime
    ) -> OutgoingMessage:
        message = self.normalize(
            {
                "message_id": f"msg-{uuid4()}",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_type": "image",
                "media_ref": media_ref,
                "timestamp": timestamp,
            }
        )
        reply = self._orchestrator.handle_message(message)
        self.send(reply)
        return reply
