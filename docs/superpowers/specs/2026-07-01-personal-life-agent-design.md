# Personal Life Agent Design

Date: 2026-07-01

Runtime baseline:

- Python 3.12.10 baseline
- PostgreSQL 16 target

## Purpose

Build a long-running personal life Agent that can be deployed on a server, use remote large model APIs for reasoning, and eventually connect to WeChat as if it were a trusted friend. The Agent should proactively check in at useful times, respond naturally to user-initiated conversations, record life data, create reminders, analyze food photos, and build a durable memory of the user's habits, preferences, goals, and state over time.

The first version should focus on a balanced MVP: life logging, health state awareness, plan execution, and companionship should all work at a useful baseline. It should not over-optimize one domain before the overall loop is stable.

## Product Positioning

The Agent is a long-term companion and lightweight coach. Its personality is hybrid:

- In daily conversation, it should feel like a warm, familiar friend.
- When discussing sleep, food, mood, body state, or plans, it should provide clear and grounded feedback.
- When the user is pursuing a goal or slipping on a pattern, it can gently push toward action.

The Agent should avoid sounding like a survey, customer-service bot, or medical authority. It should first receive the user's emotion, then analyze or record what matters.

## Scope

The first version includes:

- Natural text conversation.
- Proactive daily check-ins.
- Sleep and dream logging.
- Meal logging with food photo analysis.
- Mood, energy, body state, and plan logging.
- Reminder creation and delivery.
- Long-term memory for preferences, habits, important relationships, goals, repeated patterns, and useful strategies.
- Daily and weekly summaries.
- Manual mode switching between quiet, daily, and coach modes.
- A channel-independent messaging abstraction, with WeChat integration deferred until the Agent core is stable.

The first version does not require:

- Direct personal WeChat integration.
- Multiple users.
- A polished mobile or web app.
- Medical diagnosis, psychological diagnosis, or treatment advice.
- Outbound messages to third parties.

## Architecture

The first version uses a modular Python monolith. It is deployed as one backend service, but its internal module boundaries should be clean enough that a future Channel Gateway, worker system, or model service could be split out.

The major layers are:

1. Channel Layer
2. Agent Core
3. Memory and Profile
4. Scheduler
5. LLM Gateway
6. Storage and Observability
7. Policy and Mode Engine

The Agent Core should be channel-independent. It should process normalized messages, not WeChat-specific payloads.

## Core Modules

### Channel Adapter

The Channel Adapter receives external messages and sends Agent replies. It should not contain life-tracking or memory logic.

It normalizes incoming events into internal message objects containing:

- Message type: text, image, audio, or system.
- User ID.
- Conversation ID.
- Channel name.
- Timestamp.
- Raw content or media reference.
- Platform metadata.

The first version can use a CLI, webhook, or simple test channel. WeChat should later be added as another adapter.

### Agent Orchestrator

The Agent Orchestrator is the central decision module. It decides how to process each incoming message or scheduled task.

Its responsibilities are:

- Identify whether the user is chatting, logging life data, replying to a check-in, creating a reminder, correcting memory, or sending a food photo.
- Fetch short-term context and relevant long-term memories.
- Call the LLM Gateway for conversation, extraction, image analysis, summarization, and embeddings.
- Decide whether to reply, ask a follow-up, save a structured event, create a reminder, update memory, or change mode.
- Apply the current mode to tone, initiative, follow-up behavior, and memory thresholds.

It should not call vendor-specific APIs directly or write SQL directly.

### Memory Service

The Memory Service decides what is remembered, how it is stored, and what is recalled for a reply.

It manages:

- Raw conversation history.
- Structured life events.
- Long-term semantic memory.
- Daily, weekly, topic, and session summaries.

Not every message becomes long-term memory. Raw input is stored by default, structured life events are extracted when relevant, and long-term memory is written only for durable facts, preferences, relationships, goals, repeated patterns, or effective strategies.

### Scheduler

The Scheduler creates proactive touch tasks and reminders. It should generate intent, not final wording.

Daily mode should normally include four to five check-in windows:

- Morning: sleep, dreams, waking state.
- Lunch: meal logging and food photo analysis.
- Afternoon: energy, mood, and plan progress.
- Evening: daily review, important events, unfinished plans.
- Bedtime: wind-down, tomorrow's first step, sleep preparation.

The Scheduler checks with the Policy and Mode Engine before sending anything.

### LLM Gateway

The LLM Gateway wraps all remote model APIs behind unified interfaces.

It should support:

- Chat response generation.
- Structured extraction.
- Food image understanding.
- Summary generation.
- Embedding generation.
- Risk and safety classification.

The first version may use one provider, but business code should depend only on the gateway interface.

### Policy and Mode Engine

The Policy and Mode Engine controls autonomy, tone, interruption, and risk boundaries.

The first version supports three modes:

- Quiet mode: fewer proactive messages, lighter tone, fewer follow-ups, lower memory aggressiveness.
- Daily mode: default mode with standard check-ins, natural conversation, automatic routine logging, and high-risk confirmations.
- Coach mode: more active goal tracking, stronger plan follow-up, and short-cycle feedback.

Modes can be time-limited. Examples:

- "Today be quieter."
- "Watch my sleep this week."
- "Enter coach mode for this project."
- "Do not message me before 9 tomorrow."

Mode changes affect:

- Proactive frequency.
- Tone.
- Follow-up behavior.
- Reminder intensity.
- Memory write thresholds.
- Confirmation requirements.

### Storage Layer

The Storage Layer wraps PostgreSQL and pgvector. It owns persistence, queries, transactions, migrations, and vector search. It should not contain Agent behavior rules.

## Data Model

The database should use PostgreSQL with pgvector.

### Raw Messages

Stores all incoming and outgoing messages.

Important fields:

- Message ID.
- User ID.
- Conversation ID.
- Channel.
- Direction.
- Message type.
- Raw content or media reference.
- Timestamp.
- Related scheduled task ID.
- Platform metadata.
- Processing status.

This allows traceability, debugging, and reprocessing when extraction improves.

### Life Events

Stores structured records as a flexible `event_type + JSONB payload` model.

Event types include:

- sleep
- dream
- meal
- mood
- energy
- body_status
- plan
- reminder
- exercise
- daily_review

Each event should include:

- Occurred time.
- Recorded time.
- Source message.
- Extraction confidence.
- Structured payload.
- Estimated flag.
- User confirmation or correction status.

This flexible shape keeps the MVP adaptable. Stable event types can later receive dedicated tables if needed.

### Long-Term Memories

Stores durable facts that should shape future interaction.

Memory categories include:

- Preferences.
- Habits.
- Important relationships.
- Long-term goals.
- Repeated patterns.
- Effective strategies.

Each memory should include:

- Content.
- Category.
- Importance.
- Confidence.
- Source message or summary.
- Created time.
- Last updated time.
- Embedding.
- State: active, expired, deprecated, or denied by user.

Long-term memory must be updateable, lowerable in confidence, and forgettable.

### Conversation Summaries

Stores compressed memory at daily, weekly, topic, or session scope.

Each summary should include:

- Summary range.
- Summary type.
- Key events.
- Mood trend.
- Unfinished plans.
- Future-relevant cues.
- Embedding.

### Reminders and Tasks

Stores user-created and system-created reminders.

Important fields:

- Reminder content.
- Trigger time or rule.
- Status: pending, sent, done, cancelled, or expired.
- Repeat rule.
- Source message.
- Reminder intensity.
- Confirmation requirement.
- Completion feedback.

### User Configuration and Modes

Stores current mode and preferences.

Important fields:

- Current mode.
- Mode start time.
- Mode expiry time.
- Do-not-disturb windows.
- Daily check-in windows.
- Tone preferences.
- Memory strategy.
- Model and cost configuration.

## Main Flows

### User-Initiated Chat

Example: "Tomorrow morning I need to go to the bank. Remind me."

Flow:

1. Channel Adapter receives and normalizes the message.
2. Storage saves the raw message.
3. Agent Orchestrator detects a plan or reminder intent.
4. Memory Service retrieves relevant context.
5. LLM Gateway extracts task content, time, and missing fields.
6. The system creates a reminder if enough information exists.
7. Agent replies naturally or asks for the missing time.

### Proactive Check-In

Example: morning sleep check-in.

Flow:

1. Scheduler reaches the morning check-in window.
2. Policy and Mode Engine checks whether messaging is appropriate.
3. Scheduler creates a check-in intent.
4. Agent Orchestrator retrieves recent sleep, yesterday's events, and relevant preferences.
5. LLM Gateway generates a natural opening.
6. Channel Adapter sends the message.

### Reply to Check-In

Example: "I slept around 2, dreamed about old classmates, and woke up tired."

Flow:

1. Agent recognizes this as a reply to the morning check-in.
2. LLM Gateway extracts sleep time, dream topic, waking state, mood, and confidence.
3. Memory Service stores sleep, dream, mood, and energy events.
4. Agent asks a light follow-up only if an important field is missing.
5. Agent responds with emotional acknowledgement and a small actionable suggestion.

### Food Photo Analysis

Flow:

1. Channel Adapter receives the image and stores a media reference.
2. Agent detects a meal logging context.
3. LLM Gateway analyzes the image.
4. The system estimates food types, portion range, calories, macronutrients, and nutrition balance.
5. Memory Service stores a meal event with estimated and confidence flags.
6. Agent responds with careful uncertainty, not false precision.

### Periodic Summary

Flow:

1. Scheduler triggers an evening review or weekly summary.
2. Memory Service aggregates sleep, meals, mood, plans, and body state.
3. LLM Gateway generates observations and lightweight suggestions.
4. Agent adjusts tone by current mode.
5. Summary is stored and embedded for future recall.

## Scheduling Strategy

The scheduling model is fixed anchors plus adaptive windows plus mode control.

Daily check-ins should use windows instead of hard-coded exact times. The system should start with configurable defaults and later learn from actual user behavior.

Before each proactive message, the Scheduler asks the Policy and Mode Engine:

- Is the user in do-not-disturb time?
- Has the user recently chatted with the Agent?
- Did the user ignore the previous proactive message?
- Has the Agent already sent too many messages today?
- Does the current mode allow this check-in?
- Is there a more important reminder that should take priority?

Ordinary check-ins can be delayed, downgraded, or skipped. Important user-created reminders should retry or ask for confirmation if delivery fails.

## Safety, Privacy, and Risk Boundaries

The Agent handles intimate personal data, so safety and privacy are first-version requirements.

### Privacy

Data should be used only for the user. Logs should avoid storing full private prompts or responses unless needed for explicit debugging. Model-call logs should prefer request ID, model name, duration, token usage, error code, and a short non-sensitive summary.

### Model Context Minimization

Remote model calls should include only the context needed for the task.

Examples:

- A food analysis call should include the food image and relevant dietary preferences.
- A reminder extraction call should include the relevant message and recent scheduling context.
- A chat response should include a limited set of relevant memories and recent messages.

The system should record which memories were used to produce a response.

### Health and Psychological Safety

The Agent can provide lifestyle support but not medical diagnosis, psychological diagnosis, or treatment advice.

The Agent should shift to supportive language and suggest professional help for:

- Self-harm or suicidal statements.
- Severe physical symptoms.
- Dangerous dieting or suspected eating disorder patterns.
- Medication, diagnosis, or treatment decisions.
- Other medical-risk questions.

Food and nutrition analysis must be described as estimates.

### High-Risk Confirmation

The Agent should require confirmation before:

- Deleting large amounts of data.
- Permanently changing important long-term memory.
- Entering a long coach mode period.
- Sending messages to third parties.
- Giving strong advice in a health-risk context.
- Saving obviously sensitive long-term memory unless the user clearly asks it to remember.

### Correction and Forgetting

The user must be able to correct the Agent naturally:

- "No, I slept at 1."
- "Do not remember this."
- "You remembered that wrong."
- "Do not bring this up again."
- "Delete today's meal record."
- "Put me in quiet mode."

Corrections should update structured events, deprecate long-term memories, and adjust preferences.

## Testing and Evaluation

The first version should test both software behavior and Agent behavior.

### Functional Tests

Tests should cover:

- Normalized message intake.
- Raw message persistence.
- Text replies.
- Image message flow.
- Structured extraction for sleep, meals, mood, plans, and body state.
- Reminder create, update, cancel, send, and expire.
- Mode switching and mode expiry.
- Scheduler check-in generation.
- Model, sending, and database failure handling.

### Memory Quality Tests

Use fixed conversation samples to evaluate:

- Extraction accuracy.
- Whether long-term memory writes are important.
- Whether irrelevant small talk is ignored for long-term memory.
- Whether corrections update or deprecate memories.
- Whether retrieved memories are relevant.
- Whether sensitive content is handled carefully.

### Proactive Experience Tests

Evaluate:

- Message frequency.
- Bad timing.
- Over-follow-up after no response.
- Repetitive wording.
- Mode-specific behavior.
- User feedback such as "too annoying", "not now", or "this timing is good".

### Reply Quality Tests

Evaluate whether responses:

- Feel like a friend rather than a customer-service bot.
- Acknowledge emotion before analysis.
- Give concrete and small suggestions.
- Avoid excessive lecturing.
- Respect health and nutrition uncertainty.
- Ask natural follow-ups only when useful.

### Operational Metrics

Track:

- Daily successful check-ins.
- User response rate.
- Ignored proactive messages.
- Reminder completion rate.
- Structured event count.
- Memory created, updated, deprecated, and denied counts.
- Model calls, cost, latency, and failure rate.
- Message delivery failures.
- Database or task backlog.
- High-risk content events.

## MVP Acceptance Criteria

The MVP is accepted when:

- It can run continuously for seven days through a test channel.
- It supports four to five daily check-in windows.
- It records sleep, dreams, meals, mood, energy, body state, plans, and reminders.
- It analyzes food photos and stores estimated meal records.
- It creates and delivers reminders.
- It stores long-term memories and recalls relevant ones in later conversation.
- It supports quiet, daily, and coach modes, including time-limited mode changes.
- It has basic logging, failure retry, and model cost tracking.
- It has explicit protections for health, psychological, privacy, and deletion-risk scenarios.

## Recommended First Implementation Direction

Start with a modular Python monolith:

- `channels` for test channel and future WeChat adapter.
- `agent` for orchestration and conversation decisions.
- `memory` for recall, extraction decisions, summaries, and long-term memory rules.
- `scheduler` for proactive check-ins and reminders.
- `llm_gateway` for model abstraction.
- `policy` for modes, interruption control, and safety rules.
- `storage` for PostgreSQL and pgvector access.
- `observability` for logs, metrics, cost, and failure tracking.

This keeps the first version deployable while preserving the option to split services later.
