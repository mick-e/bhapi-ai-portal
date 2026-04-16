#!/usr/bin/env python3
"""Render environment variable management — audit, backup, and restore.

Usage:
    python deploy/render-env.py audit    # Compare Render vs .env.production
    python deploy/render-env.py backup   # Download Render env vars to .env.production
    python deploy/render-env.py restore  # Push .env.production to Render (additive, no wipe)
    python deploy/render-env.py diff     # Show what restore would change

Requires RENDER_API_KEY env var (or in .env.local).
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PROD_FILE = PROJECT_ROOT / ".env.production"
SERVICE_ID = "srv-d6hgif4r85hc739f3al0"
RENDER_API = f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars"


def get_api_key() -> str:
    key = os.environ.get("RENDER_API_KEY")
    if key:
        return key
    # Try loading from .env.local files
    for env_file in [PROJECT_ROOT / ".env.local", Path("C:/claude/littledata-mvp/.env.local")]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("RENDER_API_KEY="):
                    return line.split("=", 1)[1].strip()
    print("ERROR: RENDER_API_KEY not found. Set it as env var or in .env.local")
    sys.exit(1)


def render_request(method: str, data: dict | list | None = None) -> dict | list:
    api_key = get_api_key()
    req = urllib.request.Request(
        RENDER_API,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    if data is not None:
        req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_render_vars() -> dict[str, str]:
    data = render_request("GET")
    return {v["envVar"]["key"]: v["envVar"]["value"] for v in data}


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        print(f"ERROR: {path} not found. Run 'backup' first.")
        sys.exit(1)
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and value:
            env[key.strip()] = value.strip()
    return env


def cmd_audit():
    """Compare Render env vars against .env.production backup."""
    render_vars = get_render_vars()
    local_vars = parse_env_file(ENV_PROD_FILE)

    all_keys = sorted(set(render_vars) | set(local_vars))
    issues = []

    print(f"\n{'KEY':<40} {'RENDER':<12} {'BACKUP':<12} {'STATUS'}")
    print("-" * 85)
    for key in all_keys:
        in_render = key in render_vars
        in_local = key in local_vars
        if in_render and in_local:
            match = render_vars[key] == local_vars[key]
            status = "OK" if match else "MISMATCH"
            if not match:
                issues.append(f"  {key}: values differ")
        elif in_render:
            status = "NOT IN BACKUP"
            issues.append(f"  {key}: on Render but not in .env.production")
        else:
            status = "MISSING ON RENDER"
            issues.append(f"  {key}: in backup but missing on Render")
        print(f"  {key:<38} {'yes' if in_render else 'NO':<12} {'yes' if in_local else 'NO':<12} {status}")

    print()
    if issues:
        print(f"ISSUES ({len(issues)}):")
        for issue in issues:
            print(issue)
        print(f"\nRun 'restore' to push missing vars, or 'backup' to update .env.production")
    else:
        print("All env vars in sync.")


def cmd_backup():
    """Download current Render env vars to .env.production."""
    render_vars = get_render_vars()

    lines = [
        "# ============================================================================",
        "# Bhapi AI Portal — Production Environment (Render)",
        "# ============================================================================",
        f"# Auto-backed up by render-env.py on {__import__('datetime').date.today()}",
        "# Restore with: python deploy/render-env.py restore",
        "# ============================================================================",
        "",
    ]
    for key in sorted(render_vars):
        lines.append(f"{key}={render_vars[key]}")

    ENV_PROD_FILE.write_text("\n".join(lines) + "\n")
    print(f"Backed up {len(render_vars)} env vars to {ENV_PROD_FILE}")


def cmd_diff():
    """Show what restore would change (dry run)."""
    render_vars = get_render_vars()
    local_vars = parse_env_file(ENV_PROD_FILE)

    adds = {k: v for k, v in local_vars.items() if k not in render_vars}
    updates = {k: v for k, v in local_vars.items() if k in render_vars and render_vars[k] != v}

    if not adds and not updates:
        print("Nothing to change — Render matches .env.production")
        return

    if adds:
        print(f"\nWould ADD ({len(adds)}):")
        for k in sorted(adds):
            print(f"  + {k}")
    if updates:
        print(f"\nWould UPDATE ({len(updates)}):")
        for k in sorted(updates):
            print(f"  ~ {k}")


def cmd_restore():
    """Push .env.production to Render — ADDITIVE (merges, never wipes)."""
    render_vars = get_render_vars()
    local_vars = parse_env_file(ENV_PROD_FILE)

    # Merge: keep existing Render vars, add/update from backup
    merged = {**render_vars, **local_vars}

    if merged == render_vars:
        print("Nothing to change — Render already matches .env.production")
        return

    adds = {k for k in local_vars if k not in render_vars}
    updates = {k for k in local_vars if k in render_vars and render_vars[k] != local_vars[k]}

    print(f"Restoring to Render (additive merge):")
    if adds:
        print(f"  Adding: {', '.join(sorted(adds))}")
    if updates:
        print(f"  Updating: {', '.join(sorted(updates))}")

    # Render PUT replaces all, so we send the full merged set
    payload = [{"key": k, "value": v} for k, v in merged.items()]
    result = render_request("PUT", payload)

    if isinstance(result, list):
        print(f"\nSuccess: {len(result)} env vars now on Render")
    else:
        print(f"\nUnexpected response: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("audit", "backup", "restore", "diff"):
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    {"audit": cmd_audit, "backup": cmd_backup, "restore": cmd_restore, "diff": cmd_diff}[cmd]()
