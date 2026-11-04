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
   If it reports that `N8N_API_KEY` is missing, Richard must copy
   `example.env` to `.env` and fill it in. Don't read or write `.env`
   yourself.
2. `python3 scripts/n8n_api.py docs` — tries to download the live OpenAPI spec
   to `n8n-openapi.json`/`.yaml`. If that fails, open
   `http://localhost:5678/api/v1/docs` (Swagger playground, always exact for
   the installed version) and read the workflow/execution schemas there.
   (`docs` fetches `/api/v1/openapi.yml`.)
3. Use the spec to determine how activating/publishing works *before* any PUT
   on a workflow that is already active. A wrong assumption can deactivate a
   running workflow or leave a draft behind.

**Verified on Richard's instance (n8n Public API 1.1.1, 2026-10-29):** it uses
the draft/publish model.

- `active` is deprecated; a workflow is published when `activeVersionId` is
  not null.
- Publish/unpublish with `publish-workflow <id>` / `unpublish-workflow <id>`
  (`POST /workflows/{id}/publish|unpublish`). The old `/activate` and
  `/deactivate` endpoints are deprecated.
- `update-workflow` on a published workflow re-publishes it automatically
  (needs the `workflow:activate` API key scope). Use `--no-publish`
  (`publishIfActive=false`) to save a draft and leave the live version
  untouched.

Re-verify with `docs` if n8n has been upgraded.

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

### Secrets never go in the workflow JSON

**Treat workflow JSON as public.** Richard's workflows are backed up to
GitHub, and exports get shared. This has already gone wrong once: Discord
webhook URLs hardcoded in a Code node's JavaScript ended up in a GitHub
backup and the channels got spammed.

A secret is anything that grants access: API keys, tokens, passwords, and
**webhook URLs** (Discord, Slack, Teams, ... — the URL itself *is* the
credential), as well as URLs with a token in the path or query string.

Never put a secret as a literal anywhere in a workflow:

- Code node JavaScript/Python (constants, objects, lookup tables)
- HTTP Request URL, headers, query parameters, or body
- Set/Edit Fields values, expressions, IF/Switch conditions
- pinned data, sticky notes, node names, workflow settings

Where secrets go instead, in order of preference:

1. **n8n credentials.** Use a node with a matching credential type (e.g. the
   Discord node with its webhook connection type, the Slack node), or the
   HTTP Request node with a generic credential (Header Auth, Query Auth,
   ...). The workflow JSON then only holds a reference to the credential
   (`id` + `name`), not its value. Look up the exact credential type and node
   parameters in the live docs, as with any other node.
   Richard creates the credential in the n8n UI (Credentials) and tells you
   its name; you reference it. Don't ask him to paste the secret into this
   conversation, and don't pass it to `scripts/n8n_api.py` on a command line.
2. If no credential type fits: tell Richard and agree on an alternative
   before building (e.g. an environment variable in the n8n container read
   via `$env`, if env access is enabled). Never fall back to hardcoding.

Multiple secrets of the same kind (e.g. one Discord webhook per channel):
one credential per secret, and route items with a Switch node to one node
per credential, instead of a URL lookup table in a Code node.

The same rule applies to generator scripts in this repo
(`workflows/*.py`): reading a secret from a git-ignored file and then
writing it into the generated workflow JSON still leaks it — the result lands
in n8n and in its backups. Generators only emit credential references.

## 4. Push

**Secret check before every `create-workflow`/`update-workflow`:** scan the
JSON you are about to push, and stop if anything looks like a secret.
At minimum, search for:

```
grep -nEio 'discord(app)?\.com/api/webhooks|hooks\.slack\.com|webhook\.office\.com|xox[abpr]-|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|bearer [A-Za-z0-9._-]{16,}|(api[_-]?key|token|secret|password)["'\'' ]*[:=]' workflow.json
```

`-o` prints only the matched pattern (e.g. `discord.com/api/webhooks`,
`apiKey":`), not the secret value after it; keep it that way.
A hit means: move it to a credential (section 3), don't push. When changing
an existing workflow, run the same check on `get-workflow` output first and
tell Richard if the live version already contains hardcoded secrets.

If a secret has already been exposed (pushed to GitHub, shared, logged), tell
Richard straight away: the secret must be **rotated** (e.g. delete the
Discord webhook in Channel settings → Integrations → Webhooks and create a
new one). Removing it from the workflow or git history alone is not enough.

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
   Add `--docker-container NAME` (or set `N8N_DOCKER_CONTAINER` in `.env`) if
   n8n runs in Docker. Ask Richard if
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
- Which credentials the workflow uses (by name), and confirmation that the
  secret check found no hardcoded secrets
- Test result, including a clear notice if the test had a real side effect
  (e.g. "a Slack message was just actually sent to #channel as part of the
  test")
