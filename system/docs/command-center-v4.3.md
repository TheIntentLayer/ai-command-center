> **Note:** This document reflects V4.3 architecture. V4.4 restructured the identity folder. See the V4.4 design doc for current architecture.

# AI Command Center V4.3: Technical Specification

**Purpose:** Complete technical specification of the AI Command Center system. Sufficient for: (1) building an MCP server that exposes this system, (2) scaffolding a new user's deployment from scratch, (3) understanding every component and how they connect.

**Version:** 4.3
**Last Updated:** April 5, 2026

---

## Why This System Exists

The person using this system has a whole life. Work across multiple roles. Creative projects. Family. Health. Career strategy. Personal goals. Things they are building, things they are learning, things they are avoiding, things they dream about. No single AI conversation sees all of it, and no single conversation should have to.

Without this system, every new chat starts from zero. The person re-explains who they are, what they are working on, what rules they have established, what happened yesterday. They do this dozens of times a week. The AI has no concept of which version of the person is present right now: the one writing a book at 2 AM, the one advising a client at 8 AM, or the one planning a family trip at lunch. It loads everything or nothing. The wrong context arrives at the wrong time. And when sessions run long, even the right context fades.

This system solves that. It gives every AI instance immediate knowledge of who the person is, which mode they are operating in right now, what is in flight across their whole life, and what rules to follow. The person opens a new chat, says one word, and the AI boots up as their partner. Every conversation builds on every conversation that came before it.

If you are an AI instance reading this spec, your job is to understand this system well enough to operate within it, build on top of it, or scaffold a new deployment for a new person. If you are an engineer, this spec is sufficient to implement an MCP server, provision a new user, or extend the architecture.

---

## 1. System Overview

The AI Command Center is a personal AI partnership system that gives AI instances persistent identity, mode-aware context loading, cross-session state management, and work item tracking. It runs on Claude.ai using Claude Projects as the hosting layer.

The system solves three problems:
- **Cold start:** Every new chat starts with zero memory. The boot sequence restores full partnership context in under 60 seconds.
- **Mode switching:** A person operates in multiple cognitive modes (writing, consulting, operations, research). Each mode needs different context, tone, and behavioral rules. Personality slices handle this.
- **State drift:** Long sessions degrade context quality. The synthesizer captures state across all chats and produces a single snapshot document that any new chat can consume.

### Participants

- **Human:** The person. Makes decisions, provides corrections, drives priorities. Always present.
- **Chat instances:** Claude chat sessions, each running one personality slice. Multiple can be active simultaneously. Always present.
- **Claude Code (optional):** Terminal-based builder. Executes implementation work. Communicates through the repo, not through chat. Present only if the user does development work.

### Governing Principle

`system/` is user-agnostic. Scripts, extensions, skills, docs. Shareable across deployments.
`identity/` is sacred per-user. Core identity, slices, state, workstream registry. Never copied between users.

---

## 2. Infrastructure Layer

These are set up once by the admin per user.

### Claude.ai Project

A Claude Project provides:
- **Project instructions:** Text block injected into every chat's context window. Contains PATs, the repo URL, and the instruction to clone and follow CLAUDE.md. Character-limited. Not context-aware (same for all chats in the project).
- **Project memory:** 30 editable memory slots. High-level facts: engagement status, identity markers, key dates. Persistent across all conversations. Not structured. Claude decides when to apply.

### GitHub Repository (required)

The repo is the system of record. It holds all identity, state, and workstream data. Every chat clones it at boot.

**Required structure:**

```
repo-root/
  CLAUDE.md                          # Boot protocol (required)
  identity/                          # Per-user, sacred (required)
    core.md                          # L1: Who the person is (required)
    state/
      STATE.md                       # Current snapshot, synthesizer-generated (required)
    workstreams/
      _schema.json                   # Workstream JSON schema reference (required)
      *.json                         # One file per workstream (at least one required)
    slices/
      {name}/
        slice.md                     # L2: Personality definition (one per Tier 1 workstream)
  system/                            # User-agnostic, shared (required)
    scripts/
      az_ops.py                      # Azure DevOps CLI wrapper
      workstream.py                  # Workstream creation utility
    extensions/
      synthesizer-v2/                # Chrome extension for state synthesis
    skills/                          # Procedural guides (read on demand)
    docs/                            # Architecture and reference docs
```

**Optional identity files (per-user, created if the user's life warrants them):**

```
  identity/
    narrative.md                     # Identity narrative (for users who publish, network, or write)
    published-works.md               # Portfolio (for users with publications or products)
    governance-narrative.md          # Governance positioning (for users in governance work)
```

**Workstream content folders (created per workstream):**

```
  [workstream-name]/                 # L3: Content folders, one per workstream with a folder
  archive/                           # Historical/retired content
  ideas/                             # Tier 3 idea captures
```

### Azure DevOps (required)

Project board for work item tracking. One project per user (e.g., "My Command Center", "SS 2026").

- **Area paths** mirror workstreams. Can be nested (e.g., `ProjectName\ParentArea\ChildArea`).
- **Work item types:** Tasks (default). Tagged with workstream name and optionally functional tags (e.g., `cascade`, `daily-log`).
- **States:** To Do, Doing, Waiting, Done.
- **Access:** Via PAT stored at `~/azure-dev-ops-claude-token.txt`. All script access through `az_ops.py`.

### GitHub Wiki (optional)

Reference data that changes slowly. Cloned on demand by chat instances when a slice says to check it. Not every deployment uses a wiki. Data that would go in the wiki can also live in repo files.

Wiki repo: `{main-repo}.wiki.git`, branch `master`.

---

## 3. File Specifications

### 3.1 CLAUDE.md (required)

**Location:** Repo root.
**Read by:** Every chat instance at boot. This is the entry point.
**Purpose:** Boot protocol. Tells Claude how to initialize.

**Required sections:**

| Section | Content |
|---------|---------|
| Boot Sequence > Step 1: L1 | Read core.md, STATE.md, git log, AZ DevOps list. Universal, every chat. |
| Boot Sequence > Step 2: Determine Personality Slice | Read workstream JSONs, match trigger words, load slice. Includes default behavior when no match. |
| Boot Sequence > Step 3: Load Slice Context | Read matched slice.md and its specified files. |
| Boot Sequence > Step 4: Boot Verification | Report what was loaded. |
| Git Configuration | Identity per slice (name, email). |
| PATs | Where they come from (project instructions). Scopes and expiration. |
| State Management | Synthesizer overview. Daily log instructions. |

**Optional sections:**

| Section | When needed |
|---------|-------------|
| Wiki | If the deployment uses a GitHub Wiki. |
| Skills | If system/skills/ contains any skills. |

### 3.2 core.md (required, L1 Identity)

**Location:** `identity/core.md`
**Read by:** Every chat at boot, regardless of slice.
**Purpose:** Universal identity. Who the person is. Never changes between modes.

**Required sections:**

| Section | Content |
|---------|---------|
| Who I Am | Role, background, current phase, identity statement. Family if relevant. |
| How I Work | Working style, hours, communication preferences, energy patterns. |
| How Claude Should Operate | Behavioral directives: directness level, push-back expectations, opinion-giving, tracking requirements. |
| Hard Rules (Non-Negotiable) | Numbered list of absolute rules. These are the user's personal rules (writing style, voice, identity). Content varies entirely by user. |
| System Coordination | How participants interact. Work item governance. Daily log protocol. |
| Personality Slices Architecture | What slices are, how they relate to core.md, memory governance rules. |
| How This System Updates | Rules for when to edit core.md vs slice.md vs other files. |

**Optional sections:**

| Section | When needed |
|---------|-------------|
| Contact and Identifiers | Phone, email, ORCID, etc. If the user needs these accessible to AI. |

### 3.3 STATE.md (required, generated)

**Location:** `identity/state/STATE.md`
**Generated by:** Synthesizer v2 Chrome extension. Never hand-edited.
**Read by:** Every chat at boot.
**Purpose:** Current snapshot of everything in flight. Cross-session memory bridge.

**Required header:**

```markdown
# STATE.md

## Generated: [timestamp in user's local timezone]
## Source: In-project synthesis (DOM export + git + board)
## Generated by: Synthesizer v2
```

**Required sections:**

| Section | Content |
|---------|---------|
| The Union > Architecture | Current system version, slice count, synthesis pipeline state. Brief. |
| The Union > Active Workstreams | Per-workstream status, key facts, open items, blockers. The densest section. |
| The Union > Deadlines This Week and Coming | Table: deadline, item, status. |
| The Union > Decisions Made This Cycle | Numbered list of closed decisions. |
| The Union > New Rules Established This Cycle | Rules affecting future behavior. |
| The Union > Recent Commits (Key) | Notable commits, not exhaustive. |
| Session: [Chat Name] | Per active chat. Where it stopped. Open threads. Emotional context. |
| Where to Pick Up | Unified priority list across all sessions. Specific actions, not vague. |

**Conditional sections:**

| Section | When included |
|---------|-------------|
| Session: Claude Code | Only if the user uses Claude Code. Built from git commits. |

**Key constraint:** STATE.md must NOT duplicate information available in core.md, slice files, git log, or the AZ DevOps board. It captures only what would be lost if conversations disappeared.

### 3.4 Workstream JSON (required, at least one)

**Location:** `identity/workstreams/{name}.json`
**Schema reference:** `identity/workstreams/_schema.json`
**Read by:** CLAUDE.md boot (trigger word matching), az_ops.py (area path validation), workstream.py (provisioning).

**Full schema:**

```json
{
  "name": "string (display name)",
  "tier": "integer (1, 2, or 3)",
  "area_path": "string or null (AZ DevOps area path, supports backslash nesting)",
  "folder": "string or null (repo folder path relative to root)",
  "slice": "string or null (path to slice.md, Tier 1 only)",
  "trigger_words": "array of strings or null (boot matching, Tier 1 only)",
  "git_identity": {
    "name": "string",
    "email": "string"
  },
  "handled_by": "string or null (Tier 2: lowercase JSON filename without .json of the Tier 1 parent)",
  "active": "boolean",
  "created": "string (YYYY-MM-DD)",
  "description": "string (one-line description)"
}
```

**Tier rules:**

| Field | Tier 1 | Tier 2 | Tier 3 |
|-------|--------|--------|--------|
| slice | Required | null | null |
| trigger_words | Required | null | null |
| handled_by | null | Required | null |
| area_path | Required (or null for system-only like Synthesis) | Required | null |
| folder | Typically has one (null for thinking-only modes) | Typically has one | ideas/ |

**Nested area paths:** Use backslash notation: `"ParentArea\\ChildArea"`. Parent area path must exist in AZ DevOps before child can be created.

### 3.5 Slice Definition (required for each Tier 1 workstream)

**Location:** `identity/slices/{name}/slice.md`
**Read by:** Chat instance after boot trigger match.
**Purpose:** L2 personality. Mode-specific behavioral rules, tone, and context loading instructions.

**Required structure:**

```markdown
# Personality Slice: [Name]

**Focus:** [One-line scope description]
**System:** [What this slice is, relationship to other slices]

---

## Behavioral Rules (extends core.md)
[Rules specific to this mode. Tone, style, constraints.
These ADD TO core.md rules, they do not replace them.]

---

## What to Load

**Files (read at boot for this slice):**
[List of repo files to read immediately after boot]

**On demand:**
[Files to read when specific topics arise during conversation]
```

**Optional sections:**

| Section | When needed |
|---------|-------------|
| Wiki pages (clone and check) | If the deployment uses a wiki and this slice needs specific pages |
| Git Configuration | If this slice uses a different git identity than the default |

---

## 4. Slice Discovery

Slice discovery is how any consumer (boot sequence, MCP server, or human) determines what modes are available for a user.

**Algorithm:**

```
1. Read all .json files in identity/workstreams/
2. Exclude files starting with _ (schema, internal)
3. Filter: tier == 1 AND active == true
4. Result: list of available slices with their:
   - name (display name)
   - trigger_words (what activates this mode)
   - slice (path to the slice.md file)
   - description (one-line summary)
```

**Trigger word matching (boot):**

```
1. Take the human's first message text
2. For each Tier 1 active workstream, check if any trigger_word
   appears in the message (case-insensitive)
3. First match wins. Load that slice.
4. If no match, load the default slice (Ops or equivalent).
```

**Example discovery result:**

```json
[
  { "name": "Ops", "trigger_words": ["ops", "system", "infrastructure"], "slice": "identity/slices/ops/slice.md" },
  { "name": "Workstream-1", "trigger_words": ["workstream-1", "writing", "research"], "slice": "identity/slices/workstream-1/slice.md" }
]
```

**Context assembly for a given slice:**

When a slice is selected (by trigger match or explicit request), the full context package is:

```
L1 (universal):
  identity/core.md
  identity/state/STATE.md

L2 (mode-specific):
  The slice's slice.md file
  All files listed in the slice's "Files (read at boot)" section

L3 (on-demand, loaded during conversation):
  Files listed in the slice's "On demand" section
  Wiki pages listed in the slice's wiki section
  Workstream content folders as needed
```

This is what an MCP `get_context(slice_name)` operation would return: L1 + L2 assembled into a single context package.

---

## 5. Scripts

### az_ops.py

**Location:** `system/scripts/az_ops.py`
**Dependencies:** Python 3, stdlib only (urllib, json, base64). No pip installs.
**Auth:** Reads PAT from `~/azure-dev-ops-claude-token.txt`.
**Area paths:** Reads dynamically from `identity/workstreams/*.json` at import time. Hardcoded fallback list only if registry directory not found.

**Deployment-specific config (must be updated per user):**
- Line 31: `AZ_ORG` (Azure DevOps organization name)
- Line 32: `AZ_PROJECT` (Azure DevOps project name)

**Commands:**

| Command | Usage | Notes |
|---------|-------|-------|
| list | `az_ops.py list [--area X] [--priority N] [--state S] [--all]` | Default: active (non-Done) items |
| create | `az_ops.py create "Title" "Desc" --area X --tags T [--priority N] [--due DATE]` | Area and tags required |
| comment | `az_ops.py comment ID "Text"` | Adds comment to existing item |
| close | `az_ops.py close ID` | Transitions to Done |
| transition | `az_ops.py transition ID "State"` | Valid states: To Do, Doing, Waiting, Done |
| cascade | `az_ops.py cascade TYPE "Title" [--area X]` | Reads checklist from cascade-checklist.md |
| daily-log | `az_ops.py daily-log "Summary"` | Creates or appends to today's log item, tagged daily-log |
| create-area | `az_ops.py create-area "Name"` | Creates AZ DevOps area path |
| move-area | `az_ops.py move-area ID "NewArea"` | Moves work item to different area |

### workstream.py

**Location:** `system/scripts/workstream.py`
**Purpose:** Provisions workstream infrastructure from a JSON definition.

**Deployment-specific config (must be updated per user):**
- Line 31: `AZ_ORG`
- Line 32: `AZ_PROJECT`

**Commands:**

| Command | Usage |
|---------|-------|
| create | `workstream.py create identity/workstreams/{name}.json` |
| list | `workstream.py list` |
| sync-check | `workstream.py sync-check` |
| deactivate | `workstream.py deactivate identity/workstreams/{name}.json` |

**What `create` does:**
1. Creates AZ DevOps area path (API call)
2. Creates repo folder with .gitkeep (if specified and doesn't exist)
3. Generates slice.md from template (Tier 1 only)

Does NOT update CLAUDE.md, core.md, or az_ops.py. Those read from the registry dynamically.

---

## 6. Chrome Extensions

### Synthesizer v2

**Location:** `system/extensions/synthesizer-v2/`
**Published as:** Chrome extension via GitHub release (installable .crx or loaded unpacked)
**Purpose:** Generates STATE.md by extracting all chat transcripts from the Claude.ai DOM, analyzing each through a temporary synthesis chat, and committing the result to the repo.

**Pipeline:**

```
1. User clicks "Synthesize" in extension popup
2. Extension opens each project chat in a background tab
3. Extracts full DOM content including [THINKING] blocks
4. Creates a temporary chat named "Exclude for synthesis" in the project
5. Sends boot message -> waits for BOOT COMPLETE marker
6. Sends supplements prompt (git log, AZ board, core.md)
7. For each chat (oldest to newest):
   - Sends full transcript
   - Waits for ANALYSIS COMPLETE: {chat_name} marker
8. Sends final synthesis prompt with STATE.md format specification
9. Temp chat clones repo, writes STATE.md, commits, pushes
10. Extension deletes temp chat (unless keepChat option is checked)
```

**Per-chat extraction categories (6):**
1. What Happened
2. What Was Decided
3. What's In Progress
4. What's Next
5. How the Partnership Is Working
6. What Connects Across Chats

**Timeouts:**
- Boot: 3 minutes
- Per-chat extraction: 15 minutes
- Final synthesis: 20 minutes

**Exclude filter:** Chats with exact title "Exclude for synthesis" are skipped during DOM extraction. No other filtering.

**Key source files:**

| File | Responsibility |
|------|---------------|
| orchestrator.js | Pipeline control, marker polling, timeout management |
| prompts.js | All prompt templates with placeholder variables |
| extractor.js | DOM extraction logic |
| claude-api.js | Claude API wrapper (create/delete chat, fire completion, get state) |
| background.js | Chrome extension background script, tab management |
| popup.js / popup.html | User interface, configuration, progress display |

**Configuration:** Project ID stored in `chrome.storage.local` as `synth_project_id`. Set through the extension popup.

---

## 7. Boot Protocol

This is the exact sequence a chat instance follows when a new conversation starts.

```
1. Clone repo using GitHub PAT from project instructions
2. Read CLAUDE.md (the entry point, tells you everything below)
3. Read identity/core.md (full file, no skipping) -> L1 identity
4. Read identity/state/STATE.md (full file, no skipping) -> L1 state
5. Run: git log --oneline -20 -> recent activity
6. Write AZ PAT to ~/azure-dev-ops-claude-token.txt
7. Run: python3 system/scripts/az_ops.py list -> current work items
8. Set git identity per CLAUDE.md or slice config
9. Run slice discovery (see Section 4)
10. Match first message against discovered trigger words
11. Load matched slice.md (or default to Ops equivalent)
12. Read all files listed in slice's "Files (read at boot)" section
13. If slice specifies wiki pages: clone wiki, read those pages
14. Report what was loaded and confirm readiness (boot verification)
```

**Context loading model (L1/L2/L3):**

| Layer | What | When | Scope |
|-------|------|------|-------|
| L1 | core.md + STATE.md | Every boot, every chat | Universal identity and state |
| L2 | slice.md + slice-specified boot files | After slice selection | Mode-specific context |
| L3 | Workstream content, wiki pages, on-demand files | During conversation as needed | Task-specific detail |

---

## 8. Workstream Architecture

### What is a Workstream

A workstream is a JSON file in `identity/workstreams/`. Each file is a registry entry that tells the system three things:

- **Where do work items go?** The `area_path` field maps to an Azure DevOps area path.
- **Where do files live?** The `folder` field points to a repo folder.
- **Who handles conversations?** Either the workstream has its own `slice` (Tier 1) or it names who handles it via `handled_by` (Tier 2).

The registry is the single source of truth. CLAUDE.md, az_ops.py, and workstream.py all read from it dynamically. No hardcoded lists.

### Tiers

**Tier 1 (Thinking mode):** Gets its own slice + folder + AZ area path. Boot trigger words activate it. When you start a chat and say a trigger word, this slice's personality loads with specific files, behavioral rules, tone, and focus. One Tier 1 workstream can handle many Tier 2 workstreams underneath it.

**Tier 2 (Tracked category):** Gets a folder + AZ area path, but no slice. Work items are tracked, files exist, but conversations happen inside a Tier 1 slice. The `handled_by` field names the Tier 1 JSON filename (lowercase, without .json).

**Tier 3 (Idea):** Just a file in `ideas/`. No tracking, no folder, no slice. Ideas accumulate gravity and promote to Tier 2, then Tier 1 as they mature.

**Lifecycle:** 3 -> 2 -> 1 (promotion). Also 1 -> 2 (demotion/consolidation).

**The test:** "Does this need Claude to think differently, or just track differently?" Think differently = Tier 1. Track differently = Tier 2.

### The One-to-Many Pattern

The most important relationship in the system. One Tier 1 thinking mode handles multiple Tier 2 tracking categories.

**Example (Ops handling Tier 2 workstreams):**

```
Ops (Tier 1, slice: ops/slice.md, area_path: System)
  |-- Workstream-2 (Tier 2, handled_by: ops, area_path: Workstream-2)
  |-- Career (Tier 2, handled_by: ops, area_path: Career)
  +-- Personal (Tier 2, handled_by: ops, area_path: Personal)
```

When you talk about Career in an Ops chat, the Ops slice is loaded. Career doesn't get its own boot personality. But Career work items have their own area path, and Career files have their own folder.

**Example (nested area paths):**

```
Workstream-1 (Tier 1, slice, area_path: Workstream-1)
  |-- Workstream-3 (Tier 2, handled_by: workstream-1, area_path: Workstream-1\Workstream-3)
  +-- Sub-Project-B (Tier 2, handled_by: workstream-1, area_path: Workstream-1\Sub-Project-B)
```

### Folder Mirrors Area Path

The repo folder structure should mirror the area path hierarchy:

```
workstream-1/                  -> Workstream-1
  sub-project-a/               -> Workstream-1\Sub-Project-A
  sub-project-b/               -> Workstream-1\Sub-Project-B
  general-docs/                -> Workstream-1 (parent catches these)
```

### What Reads the Registry

- **CLAUDE.md boot sequence:** Reads Tier 1 JSONs with `active: true`, matches trigger_words to select a slice
- **az_ops.py:** Reads `area_path` from ALL JSONs (all tiers) at import time to build VALID_AREAS list
- **workstream.py:** Reads JSON definitions to provision infrastructure (area paths, folders, slice templates)

### When to Promote or Demote

**Promote (Tier 2 -> Tier 1)** when a workstream needs its own thinking mode: distinct behavioral rules, different tone, different files at boot, enough conversation volume that context loading matters.

**Demote (Tier 1 -> Tier 2)** when separate slices cause fragmentation: the workstreams are really one body of work viewed from different angles, and separate chats develop tunnel vision.

### Restructuring Steps (promotions, demotions, consolidations)

1. Update JSON files in `identity/workstreams/`
2. Move/rename repo folders if needed
3. Create, update, or delete slice files in `identity/slices/`
4. Create, rename, or move AZ DevOps area paths
5. Move affected work items to new area paths
6. Update CLAUDE.md if boot instructions reference old names
7. Run synthesis to capture new state in STATE.md

### Creating New Workstreams

For step-by-step guidance, read `system/skills/create-workstream/SKILL.md`. The skill handles tier assessment, JSON creation, and infrastructure provisioning via workstream.py.

---

## 9. New User Deployment

### What's shared vs. per-user

| Shared (copy from reference repo) | Per-user (create fresh) |
|-------------------------------------|------------------------|
| system/scripts/az_ops.py (update AZ_ORG, AZ_PROJECT) | identity/core.md |
| system/scripts/workstream.py (update AZ_ORG, AZ_PROJECT) | identity/workstreams/*.json |
| system/extensions/synthesizer-v2/ | identity/slices/*/slice.md |
| system/skills/ | identity/state/STATE.md (generated) |
| system/docs/ | Workstream content folders |
| CLAUDE.md (adapt repo URL, git identities) | Claude project instructions |
| | AZ DevOps project + area paths |
| | Optional: narrative.md, published-works.md, wiki |

### Admin setup (one-time per user)

1. Create Claude.ai project with subscription (Pro or Max)
2. Create GitHub repo (e.g., `ss-2026-command-center`)
3. Copy `system/` folder from reference implementation
4. Update deployment-specific config in az_ops.py and workstream.py (AZ_ORG, AZ_PROJECT)
5. Create `identity/` folder with subdirectories: `state/`, `workstreams/`, `slices/`
6. Create `CLAUDE.md` adapted from reference (repo URL, git identities)
7. Create Azure DevOps project for the user
8. Add GitHub PAT and AZ DevOps PAT to Claude project instructions
9. Install Synthesizer v2 Chrome extension on user's browser
10. Configure extension with the project ID

### User personalization (currently manual, target for MCP/QnA automation)

1. Create `identity/core.md` (who they are, how they work, behavioral rules, hard rules)
2. Define at least one workstream JSON in `identity/workstreams/`
3. Define at least one slice in `identity/slices/*/slice.md` (typically starts with an Ops-equivalent default)
4. Create AZ DevOps area paths (via `workstream.py create` or manual)
5. Run first synthesis to generate initial STATE.md

Optional: create narrative.md, published-works.md, wiki, additional workstreams and slices as the user's life warrants them.

### Minimum viable deployment

The simplest working deployment has:
- CLAUDE.md (boot protocol)
- identity/core.md (who they are)
- identity/state/STATE.md (can be empty initially, synthesizer generates it)
- identity/workstreams/ops.json (one Tier 1 workstream, the default)
- identity/slices/ops/slice.md (one slice definition)
- system/scripts/az_ops.py (work item tracking)
- AZ DevOps project with one area path

Everything else grows from use.

---

## 10. Cascade Checklist Pattern (optional)

**Location:** Typically in the Ops slice folder (e.g., `identity/slices/ops/cascade-checklist.md`)
**Purpose:** Runbooks for multi-surface update events.
**Invoked by:** `az_ops.py cascade TYPE "Title"` or manual reference.

The cascade pattern is a system-level concept. The specific event types and checklists are per-user. A user who publishes articles would have an "article publish" cascade. A user who doesn't publish wouldn't.

Each cascade defines: an ordered list of surfaces to update, cross-links to create, and verification steps. The `az_ops.py cascade` command reads the checklist file and embeds the steps into a new AZ DevOps work item.

---

## 11. Conventions

### Naming

- Workstream JSON filename: lowercase, hyphenated (e.g., `workstream-1.json`)
- Slice directory: matches JSON filename (e.g., `identity/slices/workstream-1/`)
- `handled_by` value: JSON filename without `.json`, lowercase
- Git identities: `Claude-{Role}` / `claude-{role}@{user-domain}`

### File governance

- Never move or delete files without explicit discussion with the human
- Never close a work item without human confirmation
- Never declare a decision confirmed before the human confirms
- Commit frequently with descriptive multi-line messages
- Pull before pushing (`git pull origin main --rebase`)

### User-specific rules

Each user defines their own writing rules, behavioral constraints, and style preferences in their core.md Hard Rules section. These are not system-level conventions. They are personal to the user and may differ completely between deployments.

---

## 12. Repositories

### Template Repo

https://github.com/aitrustcommons/ai-command-center

Public template repo. Clone to create a new command center deployment. Contains all template files with section headings and guidance text, working system/ code with config placeholders, and example workstreams across all three tiers. 34 files, ready to fill in.

### MCP Server

https://github.com/aitrustcommons/ai-command-center-mcp

Public MCP server that exposes the command center to any MCP-compatible client. Enables portability beyond Claude: Copilot, local models via Open WebUI, or any other MCP consumer can access identity, slices, state, and workstreams.

### Reference Implementation

The original deployment (Nikhil Singhal's system) lives in a private repo and serves as the reference implementation. The template repo was extracted from it with all personal content removed.
