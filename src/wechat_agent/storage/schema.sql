CREATE TABLE IF NOT EXISTS raw_messages (
  message_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  direction TEXT NOT NULL,
  message_type TEXT NOT NULL,
  content TEXT,
  media_ref TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  processing_status TEXT NOT NULL DEFAULT 'new'
);

CREATE TABLE IF NOT EXISTS life_events (
  event_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL,
  source_message_id TEXT REFERENCES raw_messages(message_id),
  confidence DOUBLE PRECISION NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  is_estimate BOOLEAN NOT NULL,
  confirmation_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS long_term_memories (
  memory_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  category TEXT NOT NULL,
  content TEXT NOT NULL,
  importance DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  source_ref TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  state TEXT NOT NULL,
  embedding JSONB
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
  task_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  trigger_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  source_message_id TEXT REFERENCES raw_messages(message_id)
);

CREATE TABLE IF NOT EXISTS mode_configs (
  user_id TEXT PRIMARY KEY,
  mode TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ,
  do_not_disturb_windows JSONB NOT NULL DEFAULT '[]',
  daily_checkin_windows JSONB NOT NULL DEFAULT '{}',
  tone_preferences JSONB NOT NULL DEFAULT '{}',
  memory_strategy TEXT NOT NULL
);
