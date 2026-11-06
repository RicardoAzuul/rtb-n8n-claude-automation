# n8n workflow builder — instructions for Claude Code

Purpose of this folder: Richard describes in plain language which n8n workflow
he wants (on his local n8n, `http://localhost:5678`), and Claude Code builds
it, tests it, and reports the result back. Richard does not have to write node
JSON or make API calls himself.

For building, changing, testing, or debugging a workflow, use the
`n8n-build-workflow` skill (`.claude/skills/n8n-build-workflow/`). It holds the
full procedure.

## Hard rule: n8n MCP only

**All interaction with n8n goes through the n8n MCP server (`mcp__n8n__*`
tools). Nothing else.** Richard would rather do something by hand than have
custom code run.

- Do NOT use `scripts/n8n_api.py`, curl, wget, Python/Node snippets, the n8n
  CLI, `docker exec`, direct database access, or any other ad-hoc code or
  shell route to reach n8n. This includes reading, listing, creating,
  updating, publishing, testing, and fetching docs.
- Do NOT write or run scripts, Code-node-style helpers, or generators to
  produce or push workflows outside the MCP tools.
- If the MCP lacks a tool or capability for what is needed (or a tool
  fails), **stop and tell Richard** exactly what is missing and what he can
  do by hand in the n8n UI. Do not work around it with another route, even
  if one exists and would be faster.
- Don't ask whether a fallback is OK. The answer is always no.
- Don't read `.env` or handle the API key. The MCP handles authentication.
- Legacy files (`scripts/n8n_api.py`, `example.env`, existing generator
  scripts) are left in place but must not be run.

Follow the MCP server's own instructions (e.g. `get_user_preferences` before
creating or modifying anything, `get_workflow_sdk_reference` and
`get_workflow_best_practices` before writing workflow code).

## Don't rely on outdated knowledge

Node schemas and capabilities differ per n8n version. Look them up with the
MCP tools (`search_nodes`, `get_node_types`, `validate_node_config`, ...)
instead of assuming, and don't invent node parameters from memory.

## Safety

- Testing runs a **real** execution, not a dry run. Always ask Richard for
  explicit confirmation before you test/publish a workflow that performs
  external, irreversible actions (email, Slack, deleting data, payments, ...).
- Never delete, archive, or overwrite an existing workflow unless Richard
  asked for it — use `update_workflow` on the right ID, not a new create,
  when it concerns a change to something existing.
- OAuth credentials can't be created via the MCP. Richard must set them up
  in the n8n UI; say so explicitly instead of acting as if it's solved.
- Never print, log, or commit secrets.
