#!/usr/bin/env python3
"""
Personality management utility.

Reads personality definitions from identity/personalities/*/personality.json
and provisions the infrastructure (AZ area path, folder, behavior file).

Because CLAUDE.md, identity-rules.md, and az_ops.py now read from the registry
dynamically, this script only needs to create the 3 things that can't
be dynamic: AZ DevOps area path, repo folder, and behavior.md file.

Usage:
  python3 personality.py create identity/personalities/omnisynth/personality.json
  python3 personality.py list
  python3 personality.py sync-check
  python3 personality.py deactivate identity/personalities/workstream-1/personality.json

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
PERSONALITIES_DIR = os.path.join(REPO_ROOT, "identity", "personalities")
TRACKING_FILE = os.path.join(REPO_ROOT, "identity", "tracking", "areas.json")

BEHAVIOR_TEMPLATE = '''# Personality: {name}

**Focus:** {description}
**System:** You are the {name} personality. Load this context when the conversation matches trigger words: {triggers}.

---

## Behavioral Rules (extends identity-rules.md)

[To be filled through use. Mode-specific rules that don't apply to other personalities.]
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


def load_personality(json_path):
    with open(json_path) as f:
        return json.load(f)


def load_all_personalities():
    personalities = []
    if not os.path.isdir(PERSONALITIES_DIR):
        return personalities
    for d in sorted(os.listdir(PERSONALITIES_DIR)):
        json_path = os.path.join(PERSONALITIES_DIR, d, "personality.json")
        if os.path.isfile(json_path):
            try:
                with open(json_path) as fh:
                    p = json.load(fh)
                    p['_dir'] = d
                    personalities.append(p)
            except (json.JSONDecodeError, KeyError):
                continue
    return personalities


def load_tracking_areas():
    if not os.path.isfile(TRACKING_FILE):
        return []
    try:
        with open(TRACKING_FILE) as f:
            data = json.load(f)
            return data.get('areas', [])
    except (json.JSONDecodeError, KeyError):
        return []


# === COMMANDS ===


def cmd_create(json_path):
    """Provision infrastructure for a personality from its JSON definition."""
    p = load_personality(json_path)
    name = p['name']
    area_path = p.get('area_path')
    folder = p.get('folder')

    print(f"Creating personality: {name}")
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

    # 3. Create behavior.md
    personality_dir = os.path.dirname(json_path)
    behavior_path = os.path.join(personality_dir, "behavior.md")
    if not os.path.exists(behavior_path):
        os.makedirs(personality_dir, exist_ok=True)
        triggers = ", ".join(p.get('trigger_words', []))
        git = p.get('git_identity', {})
        git_name = git.get('name', 'Claude-Ops') if git else 'Claude-Ops'
        git_email = git.get('email', '{YOUR_EMAIL}') if git else '{YOUR_EMAIL}'
        content = BEHAVIOR_TEMPLATE.format(
            name=name,
            description=p.get('description', ''),
            triggers=triggers,
            folder=folder or name.lower(),
            git_name=git_name,
            git_email=git_email,
        )
        with open(behavior_path, "w") as f:
            f.write(content)
        print(f"  Behavior file created: {behavior_path}")
    else:
        print(f"  Behavior file exists: {behavior_path}")

    print(f"\nDone. {name} is ready.")
    print(f"  Next: start a chat with trigger words ({', '.join(p.get('trigger_words', []))}) to use this personality.")
    print(f"  The registry is live. CLAUDE.md, identity-rules.md, and az_ops.py will pick it up automatically.")


def cmd_list():
    """List all registered personalities and tracking areas."""
    personalities = load_all_personalities()
    tracking = load_tracking_areas()

    if not personalities and not tracking:
        print("No personalities found in identity/personalities/")
        return

    active = [p for p in personalities if p.get('active')]
    inactive = [p for p in personalities if not p.get('active')]

    if active:
        print("Personalities:")
        for p in active:
            triggers = ", ".join(p.get('trigger_words', []) or [])
            print(f"  {p['name']:.<30s} {p.get('_dir', '')}")
            if triggers:
                print(f"  {'':.<30s} triggers: {triggers}")

    if tracking:
        print("\nTracking Areas:")
        for t in tracking:
            handled = t.get('handled_by', '?')
            print(f"  {t['name']:.<30s} handled by: {handled}")

    if inactive:
        print("\nInactive:")
        for p in inactive:
            print(f"  {p['name']:.<30s} (deactivated)")

    print(f"\nTotal: {len(active)} personalities, {len(tracking)} tracking areas, {len(inactive)} inactive")


def cmd_sync_check():
    """Check that all registered personalities have their infrastructure in place."""
    personalities = load_all_personalities()
    issues = []

    for p in personalities:
        if not p.get('active'):
            continue
        name = p['name']
        folder = p.get('folder')
        p_dir = p.get('_dir')

        # Check folder exists
        if folder:
            folder_full = os.path.join(REPO_ROOT, folder)
            if not os.path.exists(folder_full):
                issues.append(f"  {name}: folder '{folder}/' missing")

        # Check behavior file exists
        if p_dir:
            behavior_path = os.path.join(PERSONALITIES_DIR, p_dir, "behavior.md")
            if not os.path.exists(behavior_path):
                issues.append(f"  {name}: behavior file 'identity/personalities/{p_dir}/behavior.md' missing")

    if issues:
        print("Sync issues found:")
        for i in issues:
            print(i)
        print(f"\nRun 'personality.py create <json>' to fix.")
    else:
        print("All personalities in sync. No issues found.")


def cmd_deactivate(json_path):
    """Set a personality to inactive."""
    p = load_personality(json_path)
    p['active'] = False
    with open(json_path, 'w') as f:
        json.dump(p, f, indent=2)
        f.write('\n')
    print(f"Deactivated: {p['name']}")
    print("  Behavior file preserved (not deleted).")
    print("  Folder preserved (not deleted).")
    print("  CLAUDE.md, identity-rules.md, az_ops.py will stop showing it at next boot.")


# === MAIN ===

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  personality.py create <json-file>   Create infrastructure for a personality")
        print("  personality.py list                  List all registered personalities")
        print("  personality.py sync-check            Check infrastructure is in place")
        print("  personality.py deactivate <json>     Set personality to inactive")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create":
        if len(sys.argv) < 3:
            print("Usage: personality.py create <json-file>")
            sys.exit(1)
        cmd_create(sys.argv[2])

    elif cmd == "list":
        cmd_list()

    elif cmd == "sync-check":
        cmd_sync_check()

    elif cmd == "deactivate":
        if len(sys.argv) < 3:
            print("Usage: personality.py deactivate <json-file>")
            sys.exit(1)
        cmd_deactivate(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
