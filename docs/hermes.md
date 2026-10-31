# Hermes agent integration

The dashboard and existing Telegram worker can use the official Nous Research Hermes
agent loop with the configured local Ollama model. Set `PERSONAL_AGENT_PROVIDER=hermes`
in `backend/.env`, then restart the dashboard. Start Telegram from its dashboard page.
Do not run a separate Hermes Telegram gateway with the same bot token.

## Install

From the repository root:

```bash
.venv/bin/python backend/scripts/setup_hermes.py
```

This installs the pinned official revision in ignored `backend/data/hermes/source`,
with an isolated, upstream-managed Python environment. It skips Chromium and the
computer-use driver and does not modify your shell or existing backend environment.
The installer needs network access. `backend/data/hermes/runtime.json` records the
resolved interpreter. Run setup again after an intentional, reviewed pin update.

Official references: [repository](https://github.com/NousResearch/hermes-agent),
[setup](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart),
[configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration).

## Compatibility status

The installed revision requires **at least 64,000 context tokens**. The current
`llama3.1:8b` Ollama setup serves 4,096, so the live smoke test was rejected by
Hermes before inference. The project remains on its working Ollama agent. Hermes
is installed and integrated but is **not activated** until a compatible model is
configured and a real chat succeeds. A 64K local window substantially increases
memory requirements on this CPU machine.

For a compatible OpenAI-compatible cloud endpoint, set these in `backend/.env`:

```dotenv
HERMES_MODEL=your-provider-model-id
HERMES_BASE_URL=https://your-provider.example/v1
HERMES_API_KEY=your-private-key
HERMES_CONTEXT_TOKENS=64000
```

These are placeholders, not a working provider. Keep the API key out of chat and
Git. The bridge passes it through private process input, not command arguments or
the browser. Cloud inference sends your prompt/history and tool results to that
provider. Test before changing `PERSONAL_AGENT_PROVIDER`.

## Configuration

Keep existing credentials and add/change only:

```dotenv
PERSONAL_AGENT_PROVIDER=hermes
HERMES_DIRECTORY=data/hermes
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

Use an actually installed, tool-capable Ollama model. Hermes is orchestration software;
it still needs a working model. It does not make an 8B CPU model inherently faster.
The existing output-token and timeout settings apply. `HERMES_MODEL` and
`HERMES_BASE_URL` override the Ollama defaults; `HERMES_CONTEXT_TOKENS` must
reflect the actual model endpoint capacity and be at least 64,000. Responses stream to the dashboard;
Telegram shows typing and receives the completed response. Each turn starts an isolated
Hermes process, which adds startup cost.

## Storage and permissions

- Existing conversations, owner account, tasks and audit entries stay in the project database.
- Hermes memory and skill files live in `backend/data/hermes/home/profiles/<identity hash>/`.
  These files are private runtime data and are ignored by Git.
- Dashboard and authorized private Telegram chats share the owner identity. Group users
  receive separate Hermes memory/skill directories, matching existing task isolation.
- Task/time tools call back into the project's registry for validation, ownership checks,
  approvals and audit. The model cannot supply or change the identity used by that registry.
- Hermes's native memory and skill-document tools are enabled. Their file edits are managed
  by Hermes and do not appear as project task audit entries. Skills are instructions;
  they do not enable additional tools.
- Terminal, browser, code execution, delegation, scheduler, external publishing and the
  Hermes messaging gateway are not enabled by this bridge. This process separation is
  dependency isolation, not an operating-system sandbox.
- Dashboard signing keys and Telegram tokens are not inherited by the Hermes process.
  No cloud provider credentials are required for local Ollama.

Hermes memory begins fresh; existing chat history is provided as context on each turn.
The project remains the source of conversation history rather than Hermes's gateway
session database. New conversation sessions retain identity-scoped Hermes memory.

## Run and rollback

```bash
cd backend
../.venv/bin/personal-agent dashboard
```

The header shows `Hermes · <model>`. Telegram must be started again after restarting
the dashboard. To revert to the original loop, set `PERSONAL_AGENT_PROVIDER=ollama`
and restart. No database migration or data deletion is needed.

## Validation

The bridge integration tests exercise a real child process with a deterministic model
substitute, checking streamed text, task execution identity, credential filtering,
profile isolation and failure handling. Run them with:

```bash
.venv/bin/python -m pytest backend/tests/integration/test_hermes_agent.py
```
