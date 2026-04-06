#!/usr/bin/env python3
"""
Workstream management utility.

Reads workstream definitions from identity/workstreams/*.json and
provisions the infrastructure (AZ area path, folder, slice template).

Because CLAUDE.md, core.md, and az_ops.py now read from the registry
dynamically, this script only needs to create the 3 things that can't
be dynamic: AZ DevOps area path, repo folder, and slice.md file.

Usage:
  python3 workstream.py create identity/workstreams/omnisynth.json
  python3 workstream.py list
  python3 workstream.py sync-check
  python3 workstream.py deactivate identity/workstreams/workstream-1.json

Environment:
  AZ_DEVOPS_PAT - Azure DevOps personal access token
"""

import json
import os
import sys
import ssl
import base64
import urllib.request

# === CONFIGURATION ===

AZ_ORG = "{YOUR_AZ_ORG}"
AZ_PROJECT = "{YOUR_AZ_PROJECT}"
AZ_PROJECT_URL = AZ_PROJECT.replace(" ", "%20")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
WORKSTREAMS_DIR = os.path.join(REPO_ROOT, "identity", "workstreams")

SLICE_TEMPLATE = '''# Personality Slice: {name}

**Focus:** {description}
**System:** You are the {name} slice. Load this context when the conversation matches trigger words: {triggers}.

---

## Purpose

[To be filled through use. What this workstream is about, what kind of thinking it requires.]

---

## Behavioral Rules (extends core.md)

[To be filled through use. Mode-specific rules that don't apply to other slices.]

---

## Key Files

- `{folder}/` (workstream content folder)

---

## Git Configuration

```
git config user.name "{git_name}"
git config user.email "{git_email}"
```
'''


def _get_pat():
    pat = os.environ.get("AZ_DEVOPS_PAT", "")
    if pat:
        return pat
    for path in [
        "azure-dev-ops-claude-token.txt",
        os.path.expanduser("~/azure-dev-ops-claude-token.txt"),
    ]:
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
    print("ERROR: No Azure DevOps PAT found. Set AZ_DEVOPS_PAT.")
    sys.exit(1)


def _auth_header():
    pat = _get_pat()
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return f"Basic {encoded}"


def _az_request(url, method="GET", data=None):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Content-Type", "application/json")
    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), method=method)
        req.add_header("Authorization", _auth_header())
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read()) if resp.status != 204 else None
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": e.code, "message": body}


def load_workstream(json_path):
    with open(json_path) as f:
        return json.load(f)


def load_all_workstreams():
    workstreams = []
    if not os.path.isdir(WORKSTREAMS_DIR):
        return workstreams
    for f in sorted(os.listdir(WORKSTREAMS_DIR)):
        if f.endswith('.json') and not f.startswith('_'):
            path = os.path.join(WORKSTREAMS_DIR, f)
            try:
                with open(path) as fh:
                    ws = json.load(fh)
                    ws['_file'] = f
                    workstreams.append(ws)
            except (json.JSONDecodeError, KeyError):
                continue
    return workstreams


# === COMMANDS ===


def cmd_create(json_path):
    """Provision infrastructure for a workstream from its JSON definition."""
    ws = load_workstream(json_path)
    name = ws['name']
    tier = ws.get('tier', 1)
    area_path = ws.get('area_path')
    folder = ws.get('folder')
    slice_path = ws.get('slice')

    print(f"Creating workstream: {name} (Tier {tier})")
    print(f"  JSON: {json_path}")

    # 1. Create AZ DevOps area path
    if area_path:
        url = f"https://dev.azure.com/{AZ_ORG}/{AZ_PROJECT_URL}/_apis/wit/classificationnodes/areas?api-version=7.0"
        result = _az_request(url, method="POST", data={"name": area_path})
        if result and 'error' not in result:
            print(f"  AZ area path created: {area_path}")
        elif result and result.get('error') == 409:
            print(f"  AZ area path already exists: {area_path}")
        else:
            msg = result.get('message', '') if result else 'unknown error'
            if 'already exists' in msg.lower() or '409' in str(result.get('error', '')):
                print(f"  AZ area path already exists: {area_path}")
            else:
                print(f"  WARNING: AZ area path creation returned: {result}")

    # 2. Create folder
    if folder:
        folder_path = os.path.join(REPO_ROOT, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            # Create .gitkeep so empty folder is tracked
            with open(os.path.join(folder_path, ".gitkeep"), "w") as f:
                pass
            print(f"  Folder created: {folder}/")
        else:
            print(f"  Folder exists: {folder}/")

    # 3. Create slice.md (Tier 1 only)
    if tier == 1 and slice_path:
        full_slice_path = os.path.join(REPO_ROOT, slice_path)
        slice_dir = os.path.dirname(full_slice_path)
        if not os.path.exists(full_slice_path):
            os.makedirs(slice_dir, exist_ok=True)
            triggers = ", ".join(ws.get('trigger_words', []))
            git = ws.get('git_identity', {})
            git_name = git.get('name', 'Claude-Ops') if git else 'Claude-Ops'
            git_email = git.get('email', '{YOUR_EMAIL}') if git else '{YOUR_EMAIL}'
            content = SLICE_TEMPLATE.format(
                name=name,
                description=ws.get('description', ''),
                triggers=triggers,
                folder=folder or name.lower(),
                git_name=git_name,
                git_email=git_email,
            )
            with open(full_slice_path, "w") as f:
                f.write(content)
            print(f"  Slice created: {slice_path}")
        else:
            print(f"  Slice exists: {slice_path}")

    print(f"\nDone. {name} is ready.")
    if tier == 1:
        print(f"  Next: start a chat with trigger words ({', '.join(ws.get('trigger_words', []))}) to use this slice.")
    print(f"  The registry is live. CLAUDE.md, core.md, and az_ops.py will pick it up automatically.")


def cmd_list():
    """List all registered workstreams."""
    workstreams = load_all_workstreams()
    if not workstreams:
        print("No workstreams found in identity/workstreams/")
        return

    t1 = [w for w in workstreams if w.get('tier') == 1 and w.get('active')]
    t2 = [w for w in workstreams if w.get('tier') == 2 and w.get('active')]
    inactive = [w for w in workstreams if not w.get('active')]

    if t1:
        print("Tier 1 (Full Workstream -- slice + folder + AZ):")
        for w in t1:
            triggers = ", ".join(w.get('trigger_words', []) or [])
            print(f"  {w['name']:.<30s} {w.get('slice', 'no slice')}")
            if triggers:
                print(f"  {'':.<30s} triggers: {triggers}")

    if t2:
        print("\nTier 2 (Tracked Category -- folder + AZ, no slice):")
        for w in t2:
            handled = w.get('handled_by', '?')
            print(f"  {w['name']:.<30s} handled by: {handled}")

    if inactive:
        print("\nInactive:")
        for w in inactive:
            print(f"  {w['name']:.<30s} (deactivated)")

    print(f"\nTotal: {len(t1)} Tier 1, {len(t2)} Tier 2, {len(inactive)} inactive")


def cmd_sync_check():
    """Check that all registered workstreams have their infrastructure in place."""
    workstreams = load_all_workstreams()
    issues = []

    for ws in workstreams:
        if not ws.get('active'):
            continue
        name = ws['name']
        tier = ws.get('tier', 1)
        folder = ws.get('folder')
        slice_path = ws.get('slice')

        # Check folder exists
        if folder:
            folder_full = os.path.join(REPO_ROOT, folder)
            if not os.path.exists(folder_full):
                issues.append(f"  {name}: folder '{folder}/' missing")

        # Check slice exists (Tier 1)
        if tier == 1 and slice_path:
            slice_full = os.path.join(REPO_ROOT, slice_path)
            if not os.path.exists(slice_full):
                issues.append(f"  {name}: slice '{slice_path}' missing")

    if issues:
        print("Sync issues found:")
        for i in issues:
            print(i)
        print(f"\nRun 'workstream.py create <json>' to fix.")
    else:
        print("All workstreams in sync. No issues found.")


def cmd_deactivate(json_path):
    """Set a workstream to inactive."""
    ws = load_workstream(json_path)
    ws['active'] = False
    with open(json_path, 'w') as f:
        json.dump(ws, f, indent=2)
        f.write('\n')
    print(f"Deactivated: {ws['name']}")
    print("  Slice file preserved (not deleted).")
    print("  Folder preserved (not deleted).")
    print("  CLAUDE.md, core.md, az_ops.py will stop showing it at next boot.")


# === MAIN ===

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  workstream.py create <json-file>   Create infrastructure for a workstream")
        print("  workstream.py list                 List all registered workstreams")
        print("  workstream.py sync-check           Check infrastructure is in place")
        print("  workstream.py deactivate <json>    Set workstream to inactive")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create":
        if len(sys.argv) < 3:
            print("Usage: workstream.py create <json-file>")
            sys.exit(1)
        cmd_create(sys.argv[2])

    elif cmd == "list":
        cmd_list()

    elif cmd == "sync-check":
        cmd_sync_check()

    elif cmd == "deactivate":
        if len(sys.argv) < 3:
            print("Usage: workstream.py deactivate <json-file>")
            sys.exit(1)
        cmd_deactivate(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
