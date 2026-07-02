from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

from wechat_agent.config import DatabaseSettings
from wechat_agent.domain.events import LifeEvent, LifeEventType
from wechat_agent.domain.memory import LongTermMemory, MemoryState
from wechat_agent.domain.messages import MessageDirection, MessageType, NormalizedMessage
from wechat_agent.domain.modes import AgentMode, ModeConfig
from wechat_agent.domain.tasks import ScheduledTask, TaskStatus, TaskType
from wechat_agent.storage.store import Store


def build_postgres_store(settings: DatabaseSettings) -> Store:
    ensure_database_exists(settings)
    engine = create_postgres_engine(settings)
    initialize_schema(engine)
    return Store(
        messages=PostgresMessageRepository(engine),
        life_events=PostgresLifeEventRepository(engine),
        memories=PostgresMemoryRepository(engine),
        modes=PostgresModeRepository(engine),
        tasks=PostgresTaskRepository(engine),
    )


def create_postgres_engine(settings: DatabaseSettings) -> Engine:
    url = URL.create(
        "postgresql+psycopg",
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.name,
    )
    return create_engine(url, future=True)


def ensure_database_exists(settings: DatabaseSettings) -> None:
    admin_conn = psycopg.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        dbname="postgres",
        autocommit=True,
    )
    with admin_conn:
        with admin_conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (settings.name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(settings.name)
                    )
                )


def initialize_schema(engine: Engine) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    statements = [
        statement.strip()
        for statement in schema_path.read_text(encoding="utf-8").split(";")
        if statement.strip()
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _row_to_message(row: dict[str, Any]) -> NormalizedMessage:
    return NormalizedMessage(
        message_id=row["message_id"],
        user_id=row["user_id"],
        conversation_id=row["conversation_id"],
        channel=row["channel"],
        direction=MessageDirection(row["direction"]),
        message_type=MessageType(row["message_type"]),
        content=row["content"],
        media_ref=row["media_ref"],
        timestamp=row["timestamp"],
        metadata=row["metadata"] or {},
    )


def _row_to_event(row: dict[str, Any]) -> LifeEvent:
    return LifeEvent(
        event_id=row["event_id"],
        user_id=row["user_id"],
        event_type=LifeEventType(row["event_type"]),
        occurred_at=row["occurred_at"],
        recorded_at=row["recorded_at"],
        source_message_id=row["source_message_id"],
        confidence=row["confidence"],
        payload=row["payload"] or {},
        is_estimate=row["is_estimate"],
        confirmation_status=row["confirmation_status"],
    )


def _row_to_memory(row: dict[str, Any]) -> LongTermMemory:
    return LongTermMemory(
        memory_id=row["memory_id"],
        user_id=row["user_id"],
        category=row["category"],
        content=row["content"],
        importance=row["importance"],
        confidence=row["confidence"],
        source_ref=row["source_ref"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        state=MemoryState(row["state"]),
        embedding=row["embedding"],
    )


def _row_to_mode(row: dict[str, Any]) -> ModeConfig:
    return ModeConfig(
        user_id=row["user_id"],
        mode=AgentMode(row["mode"]),
        started_at=row["started_at"],
        expires_at=row["expires_at"],
        do_not_disturb_windows=row["do_not_disturb_windows"] or [],
        daily_checkin_windows=row["daily_checkin_windows"] or {},
        tone_preferences=row["tone_preferences"] or {},
        memory_strategy=row["memory_strategy"],
    )


def _row_to_task(row: dict[str, Any]) -> ScheduledTask:
    return ScheduledTask(
        task_id=row["task_id"],
        user_id=row["user_id"],
        conversation_id=row["conversation_id"],
        channel=row["channel"],
        task_type=TaskType(row["task_type"]),
        status=TaskStatus(row["status"]),
        trigger_at=row["trigger_at"],
        payload=row["payload"] or {},
        source_message_id=row["source_message_id"],
    )


class PostgresMessageRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, message: NormalizedMessage) -> None:
        statement = text(
            """
            INSERT INTO raw_messages (
              message_id, user_id, conversation_id, channel, direction,
              message_type, content, media_ref, timestamp, metadata, processing_status
            ) VALUES (
              :message_id, :user_id, :conversation_id, :channel, :direction,
              :message_type, :content, :media_ref, :timestamp, CAST(:metadata AS JSONB), 'new'
            )
            ON CONFLICT (message_id) DO UPDATE SET
              user_id = EXCLUDED.user_id,
              conversation_id = EXCLUDED.conversation_id,
              channel = EXCLUDED.channel,
              direction = EXCLUDED.direction,
              message_type = EXCLUDED.message_type,
              content = EXCLUDED.content,
              media_ref = EXCLUDED.media_ref,
              timestamp = EXCLUDED.timestamp,
              metadata = EXCLUDED.metadata
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "message_id": message.message_id,
                    "user_id": message.user_id,
                    "conversation_id": message.conversation_id,
                    "channel": message.channel,
                    "direction": message.direction.value,
                    "message_type": message.message_type.value,
                    "content": message.content,
                    "media_ref": message.media_ref,
                    "timestamp": message.timestamp,
                    "metadata": _json_dumps(message.metadata),
                },
            )

    def get(self, message_id: str) -> NormalizedMessage | None:
        statement = text("SELECT * FROM raw_messages WHERE message_id = :message_id")
        with self._engine.begin() as connection:
            row = connection.execute(statement, {"message_id": message_id}).mappings().first()
        return None if row is None else _row_to_message(dict(row))

    def list_recent(self, user_id: str, limit: int) -> list[NormalizedMessage]:
        statement = text(
            """
            SELECT * FROM raw_messages
            WHERE user_id = :user_id
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        )
        with self._engine.begin() as connection:
            rows = connection.execute(
                statement,
                {"user_id": user_id, "limit": limit},
            ).mappings().all()
        return [_row_to_message(dict(row)) for row in rows]


class PostgresLifeEventRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, event: LifeEvent) -> None:
        statement = text(
            """
            INSERT INTO life_events (
              event_id, user_id, event_type, occurred_at, recorded_at,
              source_message_id, confidence, payload, is_estimate, confirmation_status
            ) VALUES (
              :event_id, :user_id, :event_type, :occurred_at, :recorded_at,
              :source_message_id, :confidence, CAST(:payload AS JSONB), :is_estimate, :confirmation_status
            )
            ON CONFLICT (event_id) DO UPDATE SET
              user_id = EXCLUDED.user_id,
              event_type = EXCLUDED.event_type,
              occurred_at = EXCLUDED.occurred_at,
              recorded_at = EXCLUDED.recorded_at,
              source_message_id = EXCLUDED.source_message_id,
              confidence = EXCLUDED.confidence,
              payload = EXCLUDED.payload,
              is_estimate = EXCLUDED.is_estimate,
              confirmation_status = EXCLUDED.confirmation_status
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "event_id": event.event_id,
                    "user_id": event.user_id,
                    "event_type": event.event_type.value,
                    "occurred_at": event.occurred_at,
                    "recorded_at": event.recorded_at,
                    "source_message_id": event.source_message_id,
                    "confidence": event.confidence,
                    "payload": _json_dumps(event.payload),
                    "is_estimate": event.is_estimate,
                    "confirmation_status": event.confirmation_status,
                },
            )

    def list_for_user(
        self, user_id: str, event_type: LifeEventType | None = None
    ) -> list[LifeEvent]:
        where = "user_id = :user_id"
        params: dict[str, Any] = {"user_id": user_id}
        if event_type is not None:
            where += " AND event_type = :event_type"
            params["event_type"] = event_type.value
        statement = text(
            f"""
            SELECT * FROM life_events
            WHERE {where}
            ORDER BY recorded_at
            """
        )
        with self._engine.begin() as connection:
            rows = connection.execute(statement, params).mappings().all()
        return [_row_to_event(dict(row)) for row in rows]


class PostgresMemoryRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, memory: LongTermMemory) -> None:
        statement = text(
            """
            INSERT INTO long_term_memories (
              memory_id, user_id, category, content, importance, confidence,
              source_ref, created_at, updated_at, state, embedding
            ) VALUES (
              :memory_id, :user_id, :category, :content, :importance, :confidence,
              :source_ref, :created_at, :updated_at, :state, CAST(:embedding AS JSONB)
            )
            ON CONFLICT (memory_id) DO UPDATE SET
              user_id = EXCLUDED.user_id,
              category = EXCLUDED.category,
              content = EXCLUDED.content,
              importance = EXCLUDED.importance,
              confidence = EXCLUDED.confidence,
              source_ref = EXCLUDED.source_ref,
              created_at = EXCLUDED.created_at,
              updated_at = EXCLUDED.updated_at,
              state = EXCLUDED.state,
              embedding = EXCLUDED.embedding
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "memory_id": memory.memory_id,
                    "user_id": memory.user_id,
                    "category": memory.category,
                    "content": memory.content,
                    "importance": memory.importance,
                    "confidence": memory.confidence,
                    "source_ref": memory.source_ref,
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at,
                    "state": memory.state.value,
                    "embedding": _json_dumps(memory.embedding),
                },
            )

    def get(self, memory_id: str) -> LongTermMemory | None:
        statement = text(
            "SELECT * FROM long_term_memories WHERE memory_id = :memory_id"
        )
        with self._engine.begin() as connection:
            row = connection.execute(statement, {"memory_id": memory_id}).mappings().first()
        return None if row is None else _row_to_memory(dict(row))

    def list_active(self, user_id: str) -> list[LongTermMemory]:
        statement = text(
            """
            SELECT * FROM long_term_memories
            WHERE user_id = :user_id AND state = :state
            ORDER BY created_at
            """
        )
        with self._engine.begin() as connection:
            rows = connection.execute(
                statement,
                {"user_id": user_id, "state": MemoryState.ACTIVE.value},
            ).mappings().all()
        return [_row_to_memory(dict(row)) for row in rows]

    def replace(self, memory: LongTermMemory) -> None:
        self.save(memory)


class PostgresModeRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, user_id: str) -> ModeConfig | None:
        statement = text("SELECT * FROM mode_configs WHERE user_id = :user_id")
        with self._engine.begin() as connection:
            row = connection.execute(statement, {"user_id": user_id}).mappings().first()
        return None if row is None else _row_to_mode(dict(row))

    def save(self, config: ModeConfig) -> None:
        statement = text(
            """
            INSERT INTO mode_configs (
              user_id, mode, started_at, expires_at, do_not_disturb_windows,
              daily_checkin_windows, tone_preferences, memory_strategy
            ) VALUES (
              :user_id, :mode, :started_at, :expires_at, CAST(:do_not_disturb_windows AS JSONB),
              CAST(:daily_checkin_windows AS JSONB), CAST(:tone_preferences AS JSONB), :memory_strategy
            )
            ON CONFLICT (user_id) DO UPDATE SET
              mode = EXCLUDED.mode,
              started_at = EXCLUDED.started_at,
              expires_at = EXCLUDED.expires_at,
              do_not_disturb_windows = EXCLUDED.do_not_disturb_windows,
              daily_checkin_windows = EXCLUDED.daily_checkin_windows,
              tone_preferences = EXCLUDED.tone_preferences,
              memory_strategy = EXCLUDED.memory_strategy
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "user_id": config.user_id,
                    "mode": config.mode.value,
                    "started_at": config.started_at,
                    "expires_at": config.expires_at,
                    "do_not_disturb_windows": _json_dumps(config.do_not_disturb_windows),
                    "daily_checkin_windows": _json_dumps(config.daily_checkin_windows),
                    "tone_preferences": _json_dumps(config.tone_preferences),
                    "memory_strategy": config.memory_strategy,
                },
            )


class PostgresTaskRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, task: ScheduledTask) -> None:
        statement = text(
            """
            INSERT INTO scheduled_tasks (
              task_id, user_id, conversation_id, channel, task_type,
              status, trigger_at, payload, source_message_id
            ) VALUES (
              :task_id, :user_id, :conversation_id, :channel, :task_type,
              :status, :trigger_at, CAST(:payload AS JSONB), :source_message_id
            )
            ON CONFLICT (task_id) DO UPDATE SET
              user_id = EXCLUDED.user_id,
              conversation_id = EXCLUDED.conversation_id,
              channel = EXCLUDED.channel,
              task_type = EXCLUDED.task_type,
              status = EXCLUDED.status,
              trigger_at = EXCLUDED.trigger_at,
              payload = EXCLUDED.payload,
              source_message_id = EXCLUDED.source_message_id
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "task_id": task.task_id,
                    "user_id": task.user_id,
                    "conversation_id": task.conversation_id,
                    "channel": task.channel,
                    "task_type": task.task_type.value,
                    "status": task.status.value,
                    "trigger_at": task.trigger_at,
                    "payload": _json_dumps(task.payload),
                    "source_message_id": task.source_message_id,
                },
            )

    def list_due(self, user_id: str, now_iso: str) -> list[ScheduledTask]:
        statement = text(
            """
            SELECT * FROM scheduled_tasks
            WHERE user_id = :user_id
              AND status = :status
              AND trigger_at <= :now_iso
            ORDER BY trigger_at
            """
        )
        with self._engine.begin() as connection:
            rows = connection.execute(
                statement,
                {
                    "user_id": user_id,
                    "status": TaskStatus.PENDING.value,
                    "now_iso": now_iso,
                },
            ).mappings().all()
        return [_row_to_task(dict(row)) for row in rows]

    def status_counts(self, user_id: str) -> dict[str, int]:
        statement = text(
            """
            SELECT status, COUNT(*) AS count
            FROM scheduled_tasks
            WHERE user_id = :user_id
            GROUP BY status
            """
        )
        with self._engine.begin() as connection:
            rows = connection.execute(statement, {"user_id": user_id}).mappings().all()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        statement = text(
            """
            UPDATE scheduled_tasks
            SET status = :status
            WHERE task_id = :task_id
            """
        )
        with self._engine.begin() as connection:
            result = connection.execute(
                statement,
                {"task_id": task_id, "status": status.value},
            )
        if result.rowcount == 0:
            raise KeyError(task_id)
