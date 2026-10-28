# n8n workflow builder — instructions for Claude Code

Purpose of this folder: Richard describes in plain language which n8n workflow
he wants (on his local n8n, `http://localhost:5678`), and Claude Code builds
it via the n8n REST API, tests it, and reports the result back. Richard does
not have to write node JSON or make API calls himself.

For building, changing, testing, or debugging a workflow, use the
`n8n-build-workflow` skill (`.claude/skills/n8n-build-workflow/`). It holds the
full procedure.

Always work via `scripts/n8n_api.py` — not with ad-hoc curl commands — so the
API key never appears in a command line, log, or this conversation.

## Don't rely on outdated knowledge

The n8n API and node schemas differ per version (e.g. `active` vs. the newer
draft/publish model). Verify against the live instance
(`python3 scripts/n8n_api.py ping`, then `docs`) instead of assuming, and
don't invent node parameters from memory.

## Safety

- The API key lives in `~/.config/n8n/api_key` (chmod 600) and is only read
  by `scripts/n8n_api.py`. Never print, log, or commit it. Make sure
  `.gitignore` excludes that file and any `.env` file.
- Testing runs a **real** execution, not a dry run. Always ask Richard for
  explicit confirmation before you test/activate a workflow that performs
  external, irreversible actions (email, Slack, deleting data, payments, ...).
- Never delete or overwrite an existing workflow unless Richard asked for it
  — use `update-workflow` on the right ID, not `create-workflow` again, when
  it concerns a change to something existing.
- OAuth credentials can't be created via the API. Richard must set them up in
  the n8n UI; say so explicitly instead of acting as if it's solved.

## Config (environment variables, optional)

- `N8N_BASE_URL` — default `http://localhost:5678`
- `N8N_API_KEY_FILE` — default `~/.config/n8n/api_key`
- `N8N_API_PREFIX` — default `/api/v1`
