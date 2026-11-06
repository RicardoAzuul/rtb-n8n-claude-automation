---
name: n8n-build-workflow
description: Build, change, test, or debug an n8n workflow on Richard's local n8n instance using ONLY the n8n MCP tools (mcp__n8n__*). Use whenever Richard describes a workflow he wants, asks to modify or fix an existing one, or asks to test, publish, or unpublish one.
---

# Build an n8n workflow (n8n MCP only)

## Hard rule

Use the n8n MCP server (`mcp__n8n__*` tools) for everything. **Never** use
`scripts/n8n_api.py`, curl, Python/Node snippets, the n8n CLI, `docker exec`,
or any other custom code or shell route to reach n8n. Richard would rather do
a step by hand than have custom code run.

If the MCP can't do something, or a tool fails: **stop, tell Richard what is
missing and what he can do by hand in the n8n UI** (`http://localhost:5678`).
Don't ask about fallbacks; the answer is no. The safety rules in `CLAUDE.md`
apply throughout.

Load deferred MCP tools with ToolSearch (`select:mcp__n8n__<name>`) before
calling them.

## 1. Orient

1. `get_user_preferences` — mandatory before creating or modifying anything;
   apply what it returns.
2. `get_instance_context` — see what exists on the instance.
3. `search_workflows` / `get_workflow_details` — check whether the workflow
   (or a similar one) already exists. Changes go to the existing ID.

## 2. Clarify before building

Ask if anything is ambiguous:

- Trigger type (webhook / schedule / manual / other).
- External services and credentials involved (`list_credentials`).
- **Real, irreversible side effects** (email, Slack/Discord posts, deleting
  data, payments, ...). Tell Richard explicitly before testing: a test is a
  **real** execution, not a dry run. Get explicit confirmation first.
- Whether Richard wants a workflow or a first-class n8n Agent (follow the MCP
  server's routing guidance; never substitute one for the other silently).

## 3. Design

Read the references, then design:

- `get_workflow_sdk_reference` — required before writing workflow code.
- `get_workflow_best_practices` — once per relevant technique.
- `search_nodes`, `get_node_types`, `explore_node_resources` — look up real
  node types and parameters. Don't invent parameters from memory.
- `validate_node_config` / `validate_workflow` — validate before pushing.

If a node needs OAuth credentials that don't exist yet, they can't be created
via the MCP. Richard must set them up in the n8n UI (Credentials). Say so
explicitly.

## 4. Push

- New workflow: `create_workflow_from_code`.
- Change to an existing one: `update_workflow` on the correct ID. Never create
  a new workflow for a change, and never delete/archive/overwrite one unless
  Richard asked.
- Publishing: `publish_workflow` / `unpublish_workflow`, only when Richard
  asked or confirms. A saved draft is not a published workflow.
- Organisation (only if asked): `create_folder`, `move_workflows_to_folder`.

## 5. Test

Use the MCP only:

1. `prepare_workflow_pin_data` / `test_workflow` for a run with pinned data
   where it fits.
2. `execute_workflow` for a real run (after confirmation if there are
   external side effects).
3. Read the result with `get_workflow_execution` /
   `search_workflow_executions`. Judge `status`/`error` from that output,
   never from the fact that the call returned.

If the MCP can't run it (e.g. a trigger it can't start), ask Richard to click
"Execute workflow" in the editor, then read the result back with
`get_workflow_execution`.

## 6. Iterate

On a failed execution, read the exact error, adjust, `update_workflow`, test
again. Use `get_workflow_history` / `restore_workflow_version` only if
Richard wants to roll back. Stop after a few attempts and give Richard the
problem plus the last error message instead of retrying endlessly.

## 7. Report

Keep it short and concrete:

- Workflow name and ID
- Editor link: `http://localhost:5678/workflow/<id>`
- Published or draft
- Test result, including a clear notice if the test had a real side effect
  (e.g. "a Discord message was just actually sent as part of the test")
- Anything Richard must do by hand (credentials, UI steps)
