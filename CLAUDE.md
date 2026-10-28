# n8n workflow builder — instructions for Claude Code

Purpose of this folder: Richard describes in plain language which n8n workflow
he wants (on his local n8n, `http://localhost:5678`), and Claude Code builds
it via the n8n REST API, tests it, and reports the result back. Richard does
not have to write node JSON or make API calls himself.

Always work via `scripts/n8n_api.py` — not with ad-hoc curl commands — so the
API key never appears in a command line, log, or this conversation.

## Important warning up front: don't rely on outdated knowledge

The public n8n API has changed substantially recently: older
documentation/examples assume a simple `active: true/false` field and
separate `/activate`/`/deactivate` endpoints. More recent n8n versions have a
draft/publish model (`activeVersionId`, `publishIfActive` on the PUT), where
`active` is deprecated. Which variant applies to Richard's installed version
**must be verified live, not assumed**:

1. First run `python3 scripts/n8n_api.py ping` to verify connectivity and the
   API key.
2. Run `python3 scripts/n8n_api.py docs` — this tries to download the live
   OpenAPI spec of the running instance to `n8n-openapi.json`/`.yaml`. If
   that doesn't work automatically, open
   `http://localhost:5678/api/v1/docs` yourself (the built-in Swagger
   playground, always exactly matching the installed version) and read the
   current schemas for workflows/executions there.
3. Use that live spec to determine how activating/publishing works *before*
   you do a PUT on a workflow that is already active — a wrong assumption can
   unintentionally deactivate a running workflow or leave a draft behind.

The same applies to node types and their parameters (HTTP Request, Set, IF,
Code, Webhook, etc.): those schemas also differ per n8n version and per
installed community nodes. Don't invent node parameters from memory if you're
not sure — look them up (in the live docs, via web search for the official
n8n node documentation, or — strongly recommended if that MCP server has been
added — via `n8n-mcp` tools that know the actually installed node
definitions).

## Important limitation: there is no "run this workflow now" endpoint

The public REST API has no generic endpoint to start a workflow from scratch.
`/executions/{id}/retry` does exist, but requires an *existing* execution ID.
For a fresh test run you therefore need one of these routes, in order of
preference:

1. **n8n CLI** (most universal, works regardless of trigger type):
   `python3 scripts/n8n_api.py cli-execute <workflow-id>`
   (add `--docker-container NAME` if n8n runs in Docker — ask Richard if
   `which n8n` returns nothing and no npx n8n is available).
2. **Webhook trigger**: if the workflow starts with a Webhook node, test via
   `python3 scripts/n8n_api.py call-webhook <path> --test --data '{...}'`
   (test URL, for "Listen for test event") or without `--test` against the
   production URL if the workflow is active.
3. **Last resort**: ask Richard to click "Execute workflow" once himself in
   the n8n editor, and then read the result back via `get-execution`.

After every test run: fetch the result with
`list-executions --workflow-id <id> --limit 1` followed by
`get-execution <execution-id> --full`, and judge `status`/`error` from that —
never conclude success purely from an HTTP 200 on the trigger call itself.

## Workflow per request from Richard

1. **Clarify before building** if anything is ambiguous: which trigger type
   (webhook / schedule / manual / other), which external services/credentials
   are involved, and above all — **does the workflow have real, irreversible
   side effects** (sending email, posting a Slack message, deleting data,
   making a payment, etc.)? If so: say so explicitly to Richard before you
   start testing, because testing via this route performs a **real**
   execution, not a dry run.
2. **Design** the workflow (nodes + connections) based on the live node
   knowledge (see above) — not on assumptions.
3. **Credentials**: if a node needs OAuth credentials that don't exist yet,
   you cannot create/authorize them via the API — Richard has to do that once
   himself via the n8n UI (Credentials). Say this explicitly when you
   encounter it, instead of acting as if it's solved.
4. **Push** to n8n: `create-workflow` for new, `update-workflow` for existing
   (with `--publish`/`--no-publish` once you know from the live docs which
   behavior applies).
5. **Test** in the order above, and **iterate**: on a failed execution, read
   the exact error message from `get-execution --full`, adjust the workflow
   JSON, push again, test again. Stop after a few attempts and present the
   problem + the last error message to Richard instead of trying endlessly.
6. **Report** briefly and concretely: workflow name and ID, link to the
   editor (`http://localhost:5678/workflow/<id>`), active/inactive, and the
   test result — including a clear notice if the test had a real side effect
   (e.g. "a Slack message was just actually sent to #channel as part of the
   test").

## Safety

- The API key lives in `~/.config/n8n/api_key` (chmod 600) and is only read
  by `scripts/n8n_api.py`. Never print, log, or commit it. Make sure
  `.gitignore` in this folder (or in the repo this lives in) excludes that
  file and any `.env` file.
- Always ask Richard for explicit confirmation before you test/activate a
  workflow that performs external, irreversible actions.
- Never delete or overwrite an existing workflow unless Richard asked for it
  — use `update-workflow` on the right ID, not `create-workflow` again, when
  it concerns a change to something existing.

## Config (environment variables, optional)

- `N8N_BASE_URL` — default `http://localhost:5678`
- `N8N_API_KEY_FILE` — default `~/.config/n8n/api_key`
- `N8N_API_PREFIX` — default `/api/v1`
