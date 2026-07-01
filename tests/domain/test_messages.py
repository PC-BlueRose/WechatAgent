from datetime import UTC, datetime

from wechat_agent.domain.messages import (
    MessageDirection,
    MessageType,
    NormalizedMessage,
    OutgoingMessage,
)


def test_normalized_text_message_has_required_channel_fields():
    message = NormalizedMessage(
        message_id="msg-1",
        user_id="user-1",
        conversation_id="conv-1",
        channel="test",
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        content="I slept around 2 and woke up tired.",
        media_ref=None,
        timestamp=datetime(2026, 7, 1, 8, 30, tzinfo=UTC),
        metadata={"source": "unit-test"},
    )

    assert message.message_type is MessageType.TEXT
    assert message.direction is MessageDirection.INBOUND
    assert message.content == "I slept around 2 and woke up tired."
    assert message.metadata["source"] == "unit-test"


def test_outgoing_message_targets_a_conversation():
    outgoing = OutgoingMessage(
        conversation_id="conv-1",
        channel="test",
        content="Morning. How did you sleep last night?",
        metadata={"reason": "morning_checkin"},
    )

    assert outgoing.conversation_id == "conv-1"
    assert outgoing.channel == "test"
    assert outgoing.content.startswith("Morning")
