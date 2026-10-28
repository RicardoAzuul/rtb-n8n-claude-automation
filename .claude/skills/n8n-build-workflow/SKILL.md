---
name: n8n-build-workflow
description: Build, change, test, or debug an n8n workflow on Richard's local n8n instance via scripts/n8n_api.py. Use whenever Richard describes a workflow he wants, asks to modify or fix an existing one, or asks to test, activate, or publish one.
---

# Build an n8n workflow

Always work via `scripts/n8n_api.py`, never with ad-hoc curl commands. The
safety rules in `CLAUDE.md` apply throughout.

## 1. Verify the live API first

Don't assume the API shape. Older docs use `active: true/false` and separate
`/activate`/`/deactivate` endpoints; newer n8n versions use a draft/publish
model (`activeVersionId`, `publishIfActive` on the PUT) and deprecate `active`.

1. `python3 scripts/n8n_api.py ping` — verify connectivity and the API key.
2. `python3 scripts/n8n_api.py docs` — tries to download the live OpenAPI spec
   to `n8n-openapi.json`/`.yaml`. If that fails, open
   `http://localhost:5678/api/v1/docs` (Swagger playground, always exact for
   the installed version) and read the workflow/execution schemas there.
3. Use the spec to determine how activating/publishing works *before* any PUT
   on a workflow that is already active. A wrong assumption can deactivate a
   running workflow or leave a draft behind.

Node types and parameters (HTTP Request, Set, IF, Code, Webhook, ...) also
differ per n8n version and installed community nodes. Don't invent parameters
from memory: look them up in the live docs, the official n8n node
documentation, or `n8n-mcp` tools if that MCP server is available.

## 2. Clarify before building

Ask if anything is ambiguous:

- Trigger type (webhook / schedule / manual / other).
- External services and credentials involved.
- **Real, irreversible side effects** (sending email, posting to Slack,
  deleting data, payments, ...). If there are any, tell Richard explicitly
  before testing: testing via this route is a **real** execution, not a dry
  run. Get explicit confirmation first.

## 3. Design

Design nodes + connections from the live node knowledge above, not from
assumptions.

If a node needs OAuth credentials that don't exist yet, you cannot create or
authorize them via the API. Richard must do that once in the n8n UI
(Credentials). Say so explicitly rather than acting as if it's solved.

## 4. Push

- New workflow: `create-workflow`.
- Change to an existing one: `update-workflow` on the correct ID, with
  `--publish` or `--no-publish` once the live docs tell you which applies.
  Never use `create-workflow` again for a change, and never delete or
  overwrite an existing workflow unless Richard asked for it.

## 5. Test

There is no generic "run this workflow now" endpoint. `/executions/{id}/retry`
exists but needs an existing execution ID. Use these routes in order:

1. **n8n CLI** (works for any trigger type):
   `python3 scripts/n8n_api.py cli-execute <workflow-id>`
   Add `--docker-container NAME` if n8n runs in Docker. Ask Richard if
   `which n8n` finds nothing and no npx n8n is available.
2. **Webhook trigger**, if the workflow starts with a Webhook node:
   `python3 scripts/n8n_api.py call-webhook <path> --test --data '{...}'`
   (test URL, "Listen for test event"), or without `--test` against the
   production URL if the workflow is active.
3. **Last resort**: ask Richard to click "Execute workflow" once in the
   editor, then read the result back with `get-execution`.

After every run:

```
python3 scripts/n8n_api.py list-executions --workflow-id <id> --limit 1
python3 scripts/n8n_api.py get-execution <execution-id> --full
```

Judge `status`/`error` from that output. Never conclude success from an HTTP
200 on the trigger call.

## 6. Iterate

On a failed execution, read the exact error from `get-execution --full`,
adjust the workflow JSON, push again, test again. Stop after a few attempts
and give Richard the problem plus the last error message instead of retrying
endlessly.

## 7. Report

Keep it short and concrete:

- Workflow name and ID
- Editor link: `http://localhost:5678/workflow/<id>`
- Active or inactive
- Test result, including a clear notice if the test had a real side effect
  (e.g. "a Slack message was just actually sent to #channel as part of the
  test")
