# Personal Agent backend

Python owns agent execution, controlled tools, tasks, memory, conversation history,
SQLite persistence, approvals, audit logging, authentication, and Telegram integration.
The React UI is built in `../frontend/` and served by the backend dashboard.

## Setup

From repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e './backend[dev]'
```

Continue from `backend/`:

```bash
cp .env.example .env  # first setup only; preserve an existing configured .env
personal-agent init-dashboard
alembic upgrade head
personal-agent dashboard
```

Build the frontend first with `npm --prefix frontend run build` from repository root.
Open `http://127.0.0.1:8000`. Backend commands must run from `backend/` so `.env` and
relative SQLite paths resolve here. An existing repository-root virtual environment
can remain in place; activate it and install `./backend[dev]` from the root.

`init-dashboard` generates a signing key without displaying it and preserves other
`.env` settings. It does not change an existing key. If no owner/password exists,
registration creates one local workspace account. Existing `DASHBOARD_PASSWORD_HASH`
credentials still work, with password-only login. Registered accounts use email and
password; registration closes once the workspace has an owner. Passwords are salted
PBKDF2 hashes, and the cookie signing key is bound to current credentials.

For a registered account, recover locally with:

```bash
personal-agent reset-dashboard-password
```

This prompts without echoing the password and invalidates existing sessions. For an
environment-managed account, update its configured hash in `.env` and restart.
There is no email-based password recovery or multi-user account management yet.

## Telegram first

1. Create a bot with @BotFather and save `TELEGRAM_BOT_TOKEN` in `backend/.env`.
2. Restart the dashboard. Open Telegram in its sidebar, verify the token, and click
   Start bot. Token verification uses getMe and never sends a message.
3. Send /start to your bot. With an empty allowlist no reply is sent; its chat ID is
   recorded under Telegram activity as a blocked chat.
4. Put that numeric ID in `TELEGRAM_ALLOWED_CHAT_IDS`, restart the dashboard, and
   start the bot again. Ask a question. `/help` explains commands; `/new` starts fresh.

The dashboard can start and stop its own poller. Alternatively, run
`personal-agent telegram` in a separate terminal. Do not run both for the same bot.
Dashboard shutdown requests its own worker to stop. Stopping waits for the current
poll/answer; an external CLI process must be stopped in its own terminal.

The bot uses the same agent service and database as dashboard chat. Context is
isolated per numeric sender/chat and recovered after restart. Private allowlisted
chats share the dashboard owner’s task/memory identity; group senders remain isolated. Long replies are split
into Telegram-sized plain-text messages; malformed/unsupported updates are skipped,
and delivery errors are audited without terminating polling. Failed sends are not
blindly retried, avoiding replaying an entire multi-part answer. See the official
[Telegram Bot API](https://core.telegram.org/bots/api) for getUpdates and sendMessage.

For real answers, set `PERSONAL_AGENT_PROVIDER=ollama`, run Ollama, and install the
configured model (`OLLAMA_MODEL`, default `llama3.1:8b`). The `fake` provider remains
deterministic for tests; it does not provide intelligent answers.

The model can create/list/update its user's tasks through registry-controlled tools.
Telegram and dashboard audit events omit chat message content. Conversation history
contains messages and remains accessible to the authenticated local workspace owner.
Google Workspace, LinkedIn, and Facebook are deferred.

## Verify

```bash
python -m pytest
ruff check .
ruff format --check .
alembic history
```

Tests use temporary SQLite and mocked Telegram HTTP. New owner-account migrations
preserve existing conversation/task tables. Back up `data/agent.db` before migrations
on an established installation. Agent bootstrap still ensures missing tables for
local development; Alembic records the new account-table revision.

## Source layout

`src/personal_agent/domain/` owns rules/contracts. `application/` owns workflows,
services, permission/approval enforcement, and tools. `infrastructure/` owns model
providers, persistence, and Telegram I/O. `presentation/` owns CLI/Telegram launchers
and the web API. `app/container.py` wires adapters; `config/` owns settings/logging.
Migrations live in `migrations/`; tests live in `tests/`.

See [architecture](../docs/architecture.md) and
[structure/naming conventions](../docs/project-structure.md).


## Reply latency

The dashboard uses `/api/chat/stream` to show text as it arrives. Telegram shows a
refreshing typing indicator while inference runs. Both interfaces use a bounded
`OLLAMA_MAX_OUTPUT_TOKENS` budget (256 by default), a configurable context window,
and `OLLAMA_KEEP_ALIVE=10m`. A reply reaching its output budget says it was limited.
Increase the budget when longer responses matter more than latency.

The development-only `noop` tool is not advertised in production, and its obsolete
history entries are omitted from model input without deleting stored conversations.
Clearly informational English requests omit irrelevant built-in task/time tools;
action requests, references, other languages, and custom tools retain availability.
Every actual tool call still passes through the registry permission/approval gate.

On this CPU-only laptop, a short synthetic prompt previously took about 67 seconds
with an unnecessary tool round trip. The optimized run showed first text at about
2 seconds and finished in about 9 seconds. These are local warm-model observations,
not a guarantee for longer prompts or tool requests.

The user-approved Llama 3.2 3B download is being performed separately. The background
`scripts/activate_fast_model.py` waits for installation, validates a real task call in
a temporary database, and only then updates model settings in `.env`. It preserves
credentials and declines to overwrite a different model choice made in the meantime.
Status is in `data/fast-model-setup.json`. `ready_restart_required` means validation
succeeded and a dashboard/CLI restart is needed. Failed validation keeps the old
model. The existing 8B model remains installed.

Parameter references: [Ollama chat API](https://docs.ollama.com/api/chat) and
[Llama 3.2 model details](https://ollama.com/library/llama3.2).
