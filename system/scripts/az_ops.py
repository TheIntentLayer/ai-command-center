#!/usr/bin/env python3
"""
Azure DevOps Work Item Operations (az-ops.py)
Replaces gh-ops.sh for work item tracking via Azure DevOps Boards.

CLI Usage:
  python3 az-ops.py list                          # All open work items
  python3 az-ops.py list --area Career            # Filter by area path
  python3 az-ops.py list --priority 1             # Filter by priority
  python3 az-ops.py list --state "To Do"          # Filter by state
  python3 az-ops.py list --all                    # Include Done items
  python3 az-ops.py create "Title" "Description" --area Career --priority 1 --tags "cascade"
  python3 az-ops.py comment 42 "Comment text"
  python3 az-ops.py close 42
  python3 az-ops.py transition 42 "Doing"
  python3 az-ops.py cascade article "Article 6: AI Partnership Command Center"
  python3 az-ops.py daily-log "Posted LinkedIn Post 11, AZ#156 closed"

Import Usage:
  from az_ops import get_work_items, create_work_item, add_comment

Environment:
  AZ_DEVOPS_PAT  — Azure DevOps PAT (or reads from azure-dev-ops-claude-token.txt)
"""

import json, urllib.request, urllib.error, base64, sys, os, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# === CONFIGURATION ===

AZ_ORG = "{YOUR_AZ_ORG}"
AZ_PROJECT = "{YOUR_AZ_PROJECT}"
AZ_PROJECT_URL = AZ_PROJECT.replace(" ", "%20")

VALID_AREAS_FALLBACK = [
    "System", "Workstream-1", "Workstream-2",
    "Workstream-1\\Workstream-3"
]


def _load_valid_areas():
    """Load valid area paths from identity/workstreams/*.json registry.
    Falls back to hardcoded list if registry not found."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ws_dir = os.path.join(script_dir, "..", "..", "identity", "workstreams")
    ws_dir = os.path.normpath(ws_dir)

    if not os.path.isdir(ws_dir):
        return list(VALID_AREAS_FALLBACK)

    areas = set()
    for f in os.listdir(ws_dir):
        if f.endswith('.json') and not f.startswith('_'):
            try:
                with open(os.path.join(ws_dir, f)) as fh:
                    data = json.load(fh)
                    ap = data.get('area_path')
                    if ap:
                        areas.add(ap)
            except (json.JSONDecodeError, KeyError):
                continue

    return sorted(areas) if areas else list(VALID_AREAS_FALLBACK)


VALID_AREAS = _load_valid_areas()

VALID_STATES = ["To Do", "Doing", "Waiting", "Done"]


def _get_pat():
    """Resolve PAT from environment or token file."""
    pat = os.environ.get("AZ_DEVOPS_PAT", "")
    if pat:
        return pat
    # Try local token file
    for path in [
        "azure-dev-ops-claude-token.txt",
        os.path.expanduser("~/azure-dev-ops-claude-token.txt"),
    ]:
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
    print("ERROR: No Azure DevOps PAT found. Set AZ_DEVOPS_PAT or create azure-dev-ops-claude-token.txt")
    sys.exit(1)


def _auth_header():
    pat = _get_pat()
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return f"Basic {encoded}"


def _api_get(path):
    """GET from Azure DevOps API."""
    url = f"https://dev.azure.com/{AZ_ORG}/{AZ_PROJECT_URL}/{path}"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header()})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def _api_post(path, data, content_type="application/json"):
    """POST to Azure DevOps API."""
    url = f"https://dev.azure.com/{AZ_ORG}/{AZ_PROJECT_URL}/{path}"
    headers = {
        "Authorization": _auth_header(),
        "Content-Type": content_type,
    }
    encoded = json.dumps(data).encode()
    req = urllib.request.Request(url, data=encoded, headers=headers, method="POST")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def _api_patch(path, data):
    """PATCH to Azure DevOps API (for work item updates)."""
    url = f"https://dev.azure.com/{AZ_ORG}/{AZ_PROJECT_URL}/{path}"
    headers = {
        "Authorization": _auth_header(),
        "Content-Type": "application/json-patch+json",
    }
    encoded = json.dumps(data).encode()
    req = urllib.request.Request(url, data=encoded, headers=headers, method="PATCH")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


# ============================================================
# CORE FUNCTIONS (importable by other tools)
# ============================================================

def get_work_items(area=None, priority=None, state=None, include_done=False):
    """
    Query Azure DevOps work items via WIQL.
    Returns list of dicts with id, title, state, priority, area, tags, due_date.
    """
    conditions = ["[System.WorkItemType] = 'Issue'"]

    # Only return items from this project
    conditions.append("[System.TeamProject] = AZ_PROJECT")

    if not include_done:
        conditions.append("[System.State] <> 'Done'")

    if state:
        conditions.append(f"[System.State] = '{state}'")

    if area:
        area_path = ff"{AZ_PROJECT}\\{area}" if area in VALID_AREAS else area
        conditions.append(f"[System.AreaPath] = '{area_path}'")

    if priority:
        conditions.append(f"[Microsoft.VSTS.Common.Priority] = {priority}")

    where = " AND ".join(conditions)
    wiql = f"SELECT [System.Id] FROM WorkItems WHERE {where} ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.CreatedDate] DESC"

    result = _api_post(
        "_apis/wit/wiql?api-version=7.1",
        {"query": wiql}
    )

    ids = [item["id"] for item in result.get("workItems", [])]
    if not ids:
        return []

    # Fetch full details in batches of 200
    items = []
    for i in range(0, len(ids), 200):
        batch = ids[i:i+200]
        ids_str = ",".join(str(x) for x in batch)
        fields = "System.Id,System.Title,System.State,Microsoft.VSTS.Common.Priority,System.AreaPath,System.Tags,Microsoft.VSTS.Scheduling.DueDate,Custom.GitHubIssueNumber,System.Description"
        detail = _api_get(f"_apis/wit/workitems?ids={ids_str}&fields={fields}&api-version=7.1")
        for wi in detail.get("value", []):
            f = wi["fields"]
            area_raw = f.get("System.AreaPath", "")
            area_short = area_raw.replace(f"{AZ_PROJECT}\\", "").replace(AZ_PROJECT, "(root)")
            items.append({
                "id": wi["id"],
                "title": f.get("System.Title", ""),
                "state": f.get("System.State", ""),
                "priority": f.get("Microsoft.VSTS.Common.Priority", 0),
                "area": area_short,
                "tags": f.get("System.Tags", ""),
                "due_date": f.get("Microsoft.VSTS.Scheduling.DueDate", ""),
                "gh_issue": f.get("Custom.GitHubIssueNumber", ""),
            })

    return items


def create_work_item(title, description="", area=None, priority=3, tags="", due_date=None):
    """
    Create an Azure DevOps work item. Returns the new work item ID.
    area and tags are required -- every work item must have a workstream and tags.
    """
    if not area or area not in VALID_AREAS:
        raise ValueError(f"--area is required and must be one of: {', '.join(VALID_AREAS)}")
    if not tags:
        raise ValueError("--tags is required. Every work item needs at least one tag.")

    ops = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description or "(no description)"},
        {"op": "add", "path": "/multilineFieldsFormat/System.Description", "value": "Markdown"},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": priority},
        {"op": "add", "path": "/fields/System.AreaPath", "value": ff"{AZ_PROJECT}\\{area}"},
        {"op": "add", "path": "/fields/Custom.Workstream", "value": area},
        {"op": "add", "path": "/fields/System.Tags", "value": tags},
    ]

    if due_date:
        ops.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.DueDate", "value": due_date})

    result = _api_patch("_apis/wit/workitems/$Issue?api-version=7.1", ops)
    return result["id"]


def add_comment(work_item_id, text):
    """Add a comment to a work item."""
    url = f"_apis/wit/workitems/{work_item_id}/comments?api-version=7.1-preview.4"
    result = _api_post(url, {"text": text})
    return result.get("id")


def close_work_item(work_item_id):
    """Set work item state to Done."""
    ops = [{"op": "add", "path": "/fields/System.State", "value": "Done"}]
    result = _api_patch(f"_apis/wit/workitems/{work_item_id}?api-version=7.1", ops)
    return result["fields"]["System.State"]


def transition_work_item(work_item_id, state):
    """Set work item to any valid state."""
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state '{state}'. Must be one of: {VALID_STATES}")
    ops = [{"op": "add", "path": "/fields/System.State", "value": state}]
    result = _api_patch(f"_apis/wit/workitems/{work_item_id}?api-version=7.1", ops)
    return result["fields"]["System.State"]


def create_cascade(cascade_type, title, area=None):
    """
    Create a cascade work item by reading steps from CASCADE_CHECKLIST.md.
    Reads the relevant section and embeds steps as markdown checkboxes.
    """
    # Find cascade-checklist.md (V4: identity/slices/ops/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    checklist_paths = [
        os.path.join(script_dir, "..", "..", "identity", "slices", "ops", "cascade-checklist.md"),
        os.path.join(os.getcwd(), "identity", "slices", "ops", "cascade-checklist.md"),
        os.path.join(script_dir, "..", "context", "CASCADE_CHECKLIST.md"),
        os.path.join(os.getcwd(), "system", "context", "CASCADE_CHECKLIST.md"),
    ]

    checklist_path = None
    for p in checklist_paths:
        if os.path.exists(p):
            checklist_path = p
            break

    if not checklist_path:
        print("ERROR: CASCADE_CHECKLIST.md not found")
        return None

    with open(checklist_path) as f:
        content = f.read()

    # Map cascade type to section header
    type_map = {
        "article": "When a new article publishes",
        "book": "When a book chapter locks",
        "linkedin": "When a LinkedIn post goes live",
        "narrative": "When narrative identity updates",
        "product": "When a product ships or updates",
        "workstream": "When a new workstream starts",
        "session-close": "When a session closes",
        "resume": "When resume updates",
        "zenodo": "When Zenodo deposit is created",
    }

    section_name = type_map.get(cascade_type.lower())
    if not section_name:
        print(f"ERROR: Unknown cascade type '{cascade_type}'. Valid: {list(type_map.keys())}")
        return None

    # Extract section (between ## headers)
    # Use startswith match since some headings have parenthetical suffixes
    lines = content.split("\n")
    section_lines = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            if in_section:
                break  # hit next section
            if section_name.lower() in line.lower():
                in_section = True
                continue
        elif in_section:
            section_lines.append(line)

    if not section_lines:
        print(f"ERROR: Section containing '{section_name}' not found in CASCADE_CHECKLIST.md")
        return None

    steps = "\n".join(section_lines).strip()
    description = f"## Cascade: {section_name}\n\n{steps}"

    # Determine area from type if not specified
    if not area:
        area_map = {
            "article": "System",
            "book": "Book",
            "linkedin": "LinkedIn",
            "narrative": "System",
            "product": "Products",
            "workstream": "System",
            "session-close": "System",
            "resume": "Career",
            "zenodo": "System",
        }
        area = area_map.get(cascade_type.lower(), "System")

    work_item_id = create_work_item(
        title=title,
        description=description,
        area=area,
        priority=1,
        tags="cascade",
    )
    return work_item_id


def create_area(area_name):
    """Create a new area path under the project in Azure DevOps.

    Uses the classification nodes API. The area path must exist before
    work items can be assigned to it.
    """
    if area_name in VALID_AREAS:
        # Check if it already exists in AZ DevOps (might be in VALID_AREAS but not created yet)
        pass

    url = f"https://dev.azure.com/{AZ_ORG}/{AZ_PROJECT_URL}/_apis/wit/classificationnodes/areas?api-version=7.0"
    data = {"name": area_name}
    headers = {
        "Authorization": _auth_header(),
        "Content-Type": "application/json",
    }
    encoded = json.dumps(data).encode()
    req = urllib.request.Request(url, data=encoded, headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        return result.get("name", area_name)
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        if "already exists" in err.lower() or e.code == 409:
            return area_name  # Already exists, that's fine
        raise


def move_work_item_area(work_item_id, new_area):
    """Move a work item to a different area path and update Custom.Workstream."""
    if new_area not in VALID_AREAS:
        raise ValueError(f"Area '{new_area}' not in VALID_AREAS: {', '.join(VALID_AREAS)}")

    patches = [
        {"op": "add", "path": "/fields/System.AreaPath", "value": ff"{AZ_PROJECT}\\{new_area}"},
        {"op": "add", "path": "/fields/Custom.Workstream", "value": new_area},
    ]
    result = _api_patch(f"_apis/wit/workitems/{work_item_id}?api-version=7.0", patches)
    return result["fields"]["System.AreaPath"]


def daily_log(text):
    """Add an entry to today's daily log issue in Azure DevOps.

    Finds or creates an issue titled 'Log: March 26, 2026' (today's date in Pacific time).
    Adds the text as a comment. System-generated timestamps, always chronological.
    """
    pacific = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific)
    title = f"Log: {today.strftime('%B %-d, %Y')}"
    tag = "daily-log"

    # Search for today's log issue
    wiql = (
        f"SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] = 'Issue' AND "
        f"[System.Title] = '{title}' AND "
        f"[System.Tags] CONTAINS '{tag}' AND "
        f"[System.AreaPath] = f'{AZ_PROJECT}\\System'"
    )
    result = _api_post("_apis/wit/wiql?api-version=7.1", {"query": wiql})
    ids = [item["id"] for item in result.get("workItems", [])]

    if ids:
        # Today's issue exists, add comment
        wid = ids[0]
        add_comment(wid, text)
        return wid, False  # (id, was_created)
    else:
        # Create today's issue
        wid = create_work_item(
            title=title,
            description=f"Daily log for {today.strftime('%A, %B %-d, %Y')} (Pacific Time).",
            area="System",
            priority=3,
            tags=tag,
            due_date=today.strftime("%Y-%m-%d"),
        )
        add_comment(wid, text)
        return wid, True  # (id, was_created)


def get_comments(work_item_id):
    """Fetch all comments for a work item. Returns list of dicts with text and date."""
    url = f"_apis/wit/workitems/{work_item_id}/comments?api-version=7.1-preview.4"
    result = _api_get(url)
    comments = []
    for c in result.get("comments", []):
        comments.append({
            "text": c.get("text", ""),
            "date": c.get("createdDate", ""),
        })
    return comments


def get_daily_logs(days=7):
    """Fetch recent daily log entries from AZ DevOps.

    Returns formatted text with all daily log issues and their comments
    from the last N days, newest first.
    """
    pacific = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific)

    # Find daily-log tagged issues from last N days
    since = (today - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    wiql = (
        f"SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] = 'Issue' AND "
        f"[System.Tags] CONTAINS 'daily-log' AND "
        f"[System.TeamProject] = AZ_PROJECT AND "
        f"[System.CreatedDate] >= '{since}' "
        f"ORDER BY [System.CreatedDate] DESC"
    )
    result = _api_post("_apis/wit/wiql?api-version=7.1", {"query": wiql})
    ids = [item["id"] for item in result.get("workItems", [])]

    if not ids:
        return "[No daily log entries in the last {days} days]"

    lines = []
    for wid in ids:
        # Get issue title
        detail = _api_get(f"_apis/wit/workitems/{wid}?api-version=7.1")
        title = detail["fields"]["System.Title"]
        lines.append(f"## {title}")

        # Get comments (the actual log entries)
        comments = get_comments(wid)
        for c in comments:
            # Strip HTML tags from comment text
            text = re.sub(r'<[^>]+>', '', c["text"]).strip()
            if text:
                lines.append(f"- {text}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# CLI INTERFACE
# ============================================================

def _print_items(items):
    """Format work items for terminal display."""
    if not items:
        print("No work items found.")
        return

    print(f"{'ID':>5}  {'P':>2}  {'State':<8}  {'Area':<20}  {'Tags':<15}  {'Due':<12}  Title")
    print("-" * 110)
    for item in items:
        due = item["due_date"][:10] if item["due_date"] else ""
        tags = item["tags"][:14] if item["tags"] else ""
        print(f"{item['id']:>5}  P{item['priority']}  {item['state']:<8}  {item['area']:<20}  {tags:<15}  {due:<12}  {item['title'][:45]}")
    print(f"\n{len(items)} items")


def main():
    if len(sys.argv) < 2:
        print("Azure DevOps Work Item Operations")
        print()
        print("Usage:")
        print("  az-ops.py list [--area X] [--priority N] [--state S] [--all]")
        print("  az-ops.py create \"Title\" \"Description\" --area X --tags T [--priority N] [--due YYYY-MM-DD]")
        print("  az-ops.py comment ID \"Text\"")
        print("  az-ops.py close ID")
        print("  az-ops.py transition ID \"State\"")
        print("  az-ops.py cascade TYPE \"Title\" [--area X]")
        print("  az-ops.py daily-log \"What happened\"")
        print("  az-ops.py create-area \"AreaName\"")
        print("  az-ops.py move-area ID \"NewArea\"")
        print()
        print(f"Areas: {', '.join(VALID_AREAS)}")
        print(f"States: {', '.join(VALID_STATES)}")
        print(f"Cascade types: article, book, linkedin, narrative, product, workstream, session-close, resume, zenodo")
        sys.exit(0)

    cmd = sys.argv[1]

    try:
        if cmd == "list":
            area = None
            priority = None
            state = None
            include_done = False
            i = 2
            while i < len(sys.argv):
                if sys.argv[i] == "--area" and i + 1 < len(sys.argv):
                    area = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--priority" and i + 1 < len(sys.argv):
                    priority = int(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == "--state" and i + 1 < len(sys.argv):
                    state = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--all":
                    include_done = True
                    i += 1
                else:
                    i += 1

            items = get_work_items(area=area, priority=priority, state=state, include_done=include_done)
            _print_items(items)

        elif cmd == "create":
            if len(sys.argv) < 4:
                print("Usage: az-ops.py create \"Title\" \"Description\" --area X --tags T [--priority N] [--due YYYY-MM-DD]")
                sys.exit(1)
            title = sys.argv[2]
            description = sys.argv[3]
            area = None
            priority = 3
            tags = ""
            due_date = None
            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--area" and i + 1 < len(sys.argv):
                    area = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--priority" and i + 1 < len(sys.argv):
                    priority = int(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == "--tags" and i + 1 < len(sys.argv):
                    tags = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--due" and i + 1 < len(sys.argv):
                    due_date = sys.argv[i + 1]
                    i += 2
                else:
                    print(f"ERROR: Unknown flag '{sys.argv[i]}'. Valid: --area, --priority, --tags, --due")
                    sys.exit(1)

            # Validate required fields before creating
            if not area:
                print("ERROR: --area is required. Every work item needs a workstream.")
                print(f"Valid areas: {', '.join(VALID_AREAS)}")
                sys.exit(1)
            if not tags:
                print("ERROR: --tags is required. Every work item needs at least one tag.")
                sys.exit(1)

            wid = create_work_item(title, description, area, priority, tags, due_date)
            print(f"Created AZ#{wid}: {title}")

        elif cmd == "comment":
            if len(sys.argv) < 4:
                print("Usage: az-ops.py comment ID \"Text\"")
                sys.exit(1)
            wid = int(sys.argv[2])
            text = sys.argv[3]
            add_comment(wid, text)
            print(f"Comment added to AZ#{wid}")

        elif cmd == "close":
            if len(sys.argv) < 3:
                print("Usage: az-ops.py close ID")
                sys.exit(1)
            wid = int(sys.argv[2])
            new_state = close_work_item(wid)
            print(f"AZ#{wid} → {new_state}")

        elif cmd == "transition":
            if len(sys.argv) < 4:
                print("Usage: az-ops.py transition ID \"State\"")
                sys.exit(1)
            wid = int(sys.argv[2])
            state = sys.argv[3]
            new_state = transition_work_item(wid, state)
            print(f"AZ#{wid} → {new_state}")

        elif cmd == "cascade":
            if len(sys.argv) < 4:
                print("Usage: az-ops.py cascade TYPE \"Title\" [--area X]")
                sys.exit(1)
            cascade_type = sys.argv[2]
            title = sys.argv[3]
            area = None
            if "--area" in sys.argv:
                idx = sys.argv.index("--area")
                if idx + 1 < len(sys.argv):
                    area = sys.argv[idx + 1]
            wid = create_cascade(cascade_type, title, area)
            if wid:
                print(f"Created cascade AZ#{wid}: {title}")

        elif cmd == "daily-log":
            if len(sys.argv) < 3:
                print("Usage: az-ops.py daily-log \"What happened\"")
                sys.exit(1)
            text = sys.argv[2]
            wid, created = daily_log(text)
            if created:
                print(f"Created daily log AZ#{wid}, added entry")
            else:
                print(f"Added entry to daily log AZ#{wid}")

        elif cmd == "create-area":
            if len(sys.argv) < 3:
                print("Usage: az-ops.py create-area \"AreaName\"")
                sys.exit(1)
            area_name = sys.argv[2]
            result = create_area(area_name)
            print(ff"Area path created: {AZ_PROJECT}\\{result}")

        elif cmd == "move-area":
            if len(sys.argv) < 4:
                print("Usage: az-ops.py move-area ID \"NewArea\"")
                sys.exit(1)
            wid = int(sys.argv[2])
            new_area = sys.argv[3]
            new_path = move_work_item_area(wid, new_area)
            print(f"AZ#{wid} → {new_path}")

        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)

    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"API Error ({e.code}): {err[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
