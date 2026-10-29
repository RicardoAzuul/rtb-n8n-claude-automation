#!/usr/bin/env python3
"""
n8n_api.py — minimal, zero-dependency helper for talking to a local n8n REST API.

Design goals:
- No pip install required (stdlib only: urllib, json, argparse).
- Never prints or logs the API key.
- Does NOT hardcode assumptions about activation/publish semantics, because
  n8n's public API has changed this more than once (old: dedicated
  /activate and /deactivate endpoints with a plain boolean `active` field;
  newer versions: a draft/publish model with `activeVersionId` and a
  `publishIfActive` flag on PUT, with `active` deprecated). Always confirm
  the exact shape against the *live* docs for the installed version with
  the `docs` subcommand before relying on a specific field name.

Config: read from a `.env` file in the repo root (copy `example.env` to `.env`),
or from real environment variables, which take precedence over `.env`.
  N8N_API_KEY           required: n8n API key (Settings > n8n API in the n8n UI)
  N8N_BASE_URL          default: http://localhost:5678
  N8N_API_PREFIX        default: /api/v1
  N8N_DOCKER_CONTAINER  optional: default for `cli-execute --docker-container`

Usage:
  python3 n8n_api.py ping
  python3 n8n_api.py docs
  python3 n8n_api.py list-workflows [--active] [--limit N]
  python3 n8n_api.py get-workflow <id>
  python3 n8n_api.py create-workflow workflow.json
  python3 n8n_api.py update-workflow <id> workflow.json [--publish|--no-publish]
  python3 n8n_api.py list-executions [--workflow-id ID] [--status success|error|waiting] [--limit N]
  python3 n8n_api.py get-execution <id> [--full]
  python3 n8n_api.py retry-execution <id> [--load-workflow]
  python3 n8n_api.py cli-execute <id> [--docker-container NAME]
  python3 n8n_api.py call-webhook <path> [--method GET|POST] [--data '{"foo":"bar"}'] [--test]
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:5678"
DEFAULT_PREFIX = "/api/v1"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE lines from `path` into os.environ without overriding
    variables that are already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


load_env_file()


def get_base_url() -> str:
    return os.environ.get("N8N_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_prefix() -> str:
    return os.environ.get("N8N_API_PREFIX", DEFAULT_PREFIX)


def read_api_key() -> str:
    key = os.environ.get("N8N_API_KEY", "").strip()
    if not key:
        sys.exit(
            "N8N_API_KEY is not set.\n"
            f"Copy example.env to {ENV_FILE.name} and fill in your n8n API key\n"
            "(Settings > n8n API in the n8n UI):\n"
            f"  cp example.env .env && chmod 600 .env"
        )
    return key


def request(method: str, path: str, body=None, raw: bool = False, timeout: int = 30):
    """Low-level call. `path` is relative to base_url (not the api prefix) unless
    it already starts with the api prefix or is a full http(s) URL."""
    base = get_base_url()
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    elif path.startswith(get_prefix()):
        url = base + path
    else:
        url = base + get_prefix() + path

    headers = {"Accept": "application/json"}
    if not raw:
        headers["X-N8N-API-KEY"] = read_api_key()
        headers["Content-Type"] = "application/json"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            payload = resp.read()
    except urllib.error.HTTPError as e:
        status = e.code
        payload = e.read()
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach {url}: {e.reason}\n"
                  f"Is n8n running and is N8N_BASE_URL correct? (currently: {base})")

    text = payload.decode("utf-8", errors="replace") if payload else ""
    try:
        parsed = json.loads(text) if text else None
    except json.JSONDecodeError:
        parsed = None

    return status, parsed, text


def print_result(status, parsed, text):
    print(f"# HTTP {status}", file=sys.stderr)
    if parsed is not None:
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    else:
        print(text)


# ---- subcommands -----------------------------------------------------------

def cmd_ping(args):
    status, parsed, text = request("GET", "/workflows?limit=1")
    if status == 200:
        print(f"OK — reached n8n at {get_base_url()} and authenticated (HTTP 200).")
    elif status in (401, 403):
        print(f"Reached n8n at {get_base_url()} but the API key was rejected (HTTP {status}).",
              file=sys.stderr)
        sys.exit(1)
    else:
        print_result(status, parsed, text)
        sys.exit(1)


def cmd_docs(args):
    """Best-effort fetch of the live API reference for THIS installed n8n version.
    Do not assume any one of these paths is correct — n8n's docs tooling has
    changed across versions. Try a few conventional spots and report what worked."""
    base = get_base_url()
    candidates = [
        get_prefix() + "/docs/openapi.json",
        get_prefix() + "/docs/json",
        get_prefix() + "/docs-json",
        get_prefix() + "/docs/yaml",
    ]
    found = False
    for c in candidates:
        status, parsed, text = request("GET", c)
        if status == 200 and (parsed is not None or "openapi" in text.lower() or "swagger" in text.lower()):
            out = Path("n8n-openapi" + (".json" if parsed is not None else ".yaml"))
            out.write_text(text, encoding="utf-8")
            print(f"Saved live API spec from {base}{c} -> {out.resolve()}")
            found = True
            break
    if not found:
        print(
            f"Could not auto-fetch a raw spec file. Open {base}{get_prefix()}/docs in a "
            f"browser instead (the interactive Swagger playground) — it always reflects "
            f"the exact version installed, use 'Authorize' with the API key, and confirm "
            f"field names (e.g. whether workflows still use a plain 'active' boolean, or "
            f"the newer 'activeVersionId' / 'publishIfActive' draft-publish model) before "
            f"writing automation against them.",
            file=sys.stderr,
        )


def cmd_list_workflows(args):
    q = []
    if args.active:
        q.append("active=true")
    if args.limit:
        q.append(f"limit={args.limit}")
    qs = ("?" + "&".join(q)) if q else ""
    print_result(*request("GET", "/workflows" + qs))


def cmd_get_workflow(args):
    print_result(*request("GET", f"/workflows/{args.id}"))


def cmd_create_workflow(args):
    body = json.loads(Path(args.file).read_text(encoding="utf-8"))
    print_result(*request("POST", "/workflows", body=body))


def cmd_update_workflow(args):
    body = json.loads(Path(args.file).read_text(encoding="utf-8"))
    path = f"/workflows/{args.id}"
    if args.publish is not None:
        path += f"?publishIfActive={'true' if args.publish else 'false'}"
    print_result(*request("PUT", path, body=body))


def cmd_list_executions(args):
    q = []
    if args.workflow_id:
        q.append(f"workflowId={args.workflow_id}")
    if args.status:
        q.append(f"status={args.status}")
    if args.limit:
        q.append(f"limit={args.limit}")
    qs = ("?" + "&".join(q)) if q else ""
    print_result(*request("GET", "/executions" + qs))


def cmd_get_execution(args):
    qs = "?includeData=true" if args.full else ""
    print_result(*request("GET", f"/executions/{args.id}" + qs))


def cmd_retry_execution(args):
    body = {"loadWorkflow": bool(args.load_workflow)}
    print_result(*request("POST", f"/executions/{args.id}/retry", body=body))


def cmd_cli_execute(args):
    """Run a workflow by ID via the n8n CLI — the one trigger-agnostic way to
    force a fresh execution, since the public REST API has no generic
    'run this workflow now' endpoint (only /executions/{id}/retry, which
    needs an execution that already exists)."""
    base_cmd = None
    container = args.docker_container or os.environ.get("N8N_DOCKER_CONTAINER")
    if container:
        base_cmd = ["docker", "exec", container, "n8n", "execute", f"--id={args.id}"]
    else:
        from shutil import which
        if which("n8n"):
            base_cmd = ["n8n", "execute", f"--id={args.id}"]
        else:
            base_cmd = ["npx", "--yes", "n8n", "execute", f"--id={args.id}"]
    print(f"$ {' '.join(base_cmd)}", file=sys.stderr)
    result = subprocess.run(base_cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


def cmd_call_webhook(args):
    base = get_base_url()
    kind = "webhook-test" if args.test else "webhook"
    path = args.path.lstrip("/")
    url = f"{base}/{kind}/{path}"
    body = json.loads(args.data) if args.data else None
    status, parsed, text = request(args.method, url, body=body, raw=True)
    print_result(status, parsed, text)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping").set_defaults(func=cmd_ping)
    sub.add_parser("docs").set_defaults(func=cmd_docs)

    s = sub.add_parser("list-workflows")
    s.add_argument("--active", action="store_true")
    s.add_argument("--limit", type=int)
    s.set_defaults(func=cmd_list_workflows)

    s = sub.add_parser("get-workflow")
    s.add_argument("id")
    s.set_defaults(func=cmd_get_workflow)

    s = sub.add_parser("create-workflow")
    s.add_argument("file")
    s.set_defaults(func=cmd_create_workflow)

    s = sub.add_parser("update-workflow")
    s.add_argument("id")
    s.add_argument("file")
    grp = s.add_mutually_exclusive_group()
    grp.add_argument("--publish", dest="publish", action="store_true", default=None)
    grp.add_argument("--no-publish", dest="publish", action="store_false")
    s.set_defaults(func=cmd_update_workflow)

    s = sub.add_parser("list-executions")
    s.add_argument("--workflow-id")
    s.add_argument("--status", choices=["success", "error", "waiting"])
    s.add_argument("--limit", type=int)
    s.set_defaults(func=cmd_list_executions)

    s = sub.add_parser("get-execution")
    s.add_argument("id")
    s.add_argument("--full", action="store_true", help="include full execution data, not just summary")
    s.set_defaults(func=cmd_get_execution)

    s = sub.add_parser("retry-execution")
    s.add_argument("id")
    s.add_argument("--load-workflow", action="store_true",
                    help="use the currently saved workflow instead of the version from the original run")
    s.set_defaults(func=cmd_retry_execution)

    s = sub.add_parser("cli-execute")
    s.add_argument("id")
    s.add_argument("--docker-container", help="run via `docker exec <name> n8n execute ...` instead of a local n8n binary")
    s.set_defaults(func=cmd_cli_execute)

    s = sub.add_parser("call-webhook")
    s.add_argument("path")
    s.add_argument("--method", default="POST")
    s.add_argument("--data", help="raw JSON body string")
    s.add_argument("--test", action="store_true", help="hit the webhook-test URL instead of the production one")
    s.set_defaults(func=cmd_call_webhook)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
