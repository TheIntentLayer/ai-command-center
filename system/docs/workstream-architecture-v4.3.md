# Workstream Architecture Reference

**Purpose:** Conceptual model for workstreams, tiers, slices, and how they relate. Read this before creating, promoting, or restructuring workstreams.

**Last Updated:** April 5, 2026

---

## Core Concepts

### Workstream

A workstream is a JSON file in `identity/workstreams/`. Each file is a registry entry that tells the system three things:

- **Where do work items go?** The `area_path` field maps to an Azure DevOps area path.
- **Where do files live?** The `folder` field points to a repo folder.
- **Who handles conversations?** Either the workstream has its own `slice` (Tier 1) or it names who handles it via `handled_by` (Tier 2).

The registry is the single source of truth. CLAUDE.md, az_ops.py, and workstream.py all read from it dynamically.

### Tiers

Tiers determine how much infrastructure a workstream gets.

**Tier 1: Thinking mode.** Gets a slice + folder + AZ area path. When you start a chat and say a trigger word, this slice's personality loads: specific files, behavioral rules, tone, focus. One Tier 1 workstream can handle many Tier 2 workstreams underneath it.

**Tier 2: Tracked category.** Gets a folder + AZ area path, but no slice. Work items are tracked, files exist, but conversations happen inside a Tier 1 slice. The `handled_by` field names the Tier 1 JSON filename (lowercase, without .json).

**Tier 3: Idea.** Just a file in `ideas/`. No tracking, no folder, no slice. Ideas accumulate gravity and promote to Tier 2, then Tier 1 as they mature.

Lifecycle flows: 3 -> 2 -> 1. But also 1 -> 2 when a workstream loses independent thinking-mode status (consolidation).

### Slice

A file at `identity/slices/{name}/slice.md`. Defines:

- Focus and scope
- Behavioral rules (extending core.md)
- Tone and conversation posture
- Files to load at boot
- Wiki pages to check

The boot sequence reads the first message, matches trigger words from all Tier 1 JSONs, and loads the matching slice. If no trigger matches, Ops loads as default.

### Area Paths

Azure DevOps area paths for work item categorization. They can be nested using backslash notation:

```
Your-Project\Workstream-1                     (parent)
Your-Project\Workstream-1\Workstream-3       (child)
Your-Project\Workstream-1\Sub-Project-B      (child)
```

A Tier 1 workstream can have a parent area path, with its Tier 2 children nesting underneath. Work items at the parent level catch general work; children catch specific threads.

az_ops.py reads `area_path` from every JSON file (all tiers) to build the VALID_AREAS list.

---

## Key Relationships

### One Tier 1, Many Tier 2s

This is the most important pattern. One thinking mode handles multiple tracking categories.

**Example (Ops):**

```
Ops (Tier 1, slice: ops/slice.md, area_path: System)
  ├── LinkedIn (Tier 2, handled_by: ops, area_path: LinkedIn)
  ├── Career (Tier 2, handled_by: ops, area_path: Career)
  ├── Products (Tier 2, handled_by: ops, area_path: Products)
  ├── Personal (Tier 2, handled_by: ops, area_path: Personal)
  └── Personal (Tier 2, handled_by: ops, area_path: Personal)
```

When you talk about LinkedIn in an Ops chat, the Ops slice is loaded. LinkedIn doesn't get its own boot personality. But LinkedIn work items have their own area path, and LinkedIn files have their own folder.

**Example (AI Trust Commons):**

```
Workstream-1 (Tier 1, slice, area_path: Workstream-1)
  ├── Workstream-3 (Tier 2, handled_by: workstream-1, area_path: Workstream-1\Workstream-3)
  └── (Other sub-projects at parent area path)
```

### Folder Mirrors Area Path

The repo folder structure should mirror the area path hierarchy:

```
workstream-1/                  -> Workstream-1
  workstream-3/                -> Workstream-1\Workstream-3
  sub-project-b/               -> Workstream-1 (parent catches these)
```

### When to Promote or Demote

**Promote (Tier 2 -> Tier 1)** when a workstream needs its own thinking mode: distinct behavioral rules, different tone, different files at boot, enough volume that context loading matters. For example, consulting work might require a completely different posture than general operations.

**Demote (Tier 1 -> Tier 2)** when separate slices cause fragmentation: the workstreams are really one body of work viewed from different angles, and separate chats develop tunnel vision.

**The test:** "Does this workstream need Claude to think differently, or just track differently?" If track differently, it's Tier 2. If think differently, it's Tier 1.

---

## Registry Mechanics

### JSON Fields

| Field | Purpose | Tier 1 | Tier 2 |
|-------|---------|--------|--------|
| name | Display name | Required | Required |
| tier | 1, 2, or 3 | 1 | 2 |
| area_path | AZ DevOps area | Required (or null for thinking-only modes like Synthesis) | Required |
| folder | Repo folder | Required (or null) | Required (or null) |
| slice | Path to slice.md | Required | null |
| trigger_words | Boot matching | Required | null |
| handled_by | Parent slice | null | Required (lowercase JSON filename without .json) |
| active | Currently in use | boolean | boolean |

### What Reads the Registry

- **CLAUDE.md boot:** Reads Tier 1 JSONs with `active: true`, matches trigger_words
- **az_ops.py:** Reads `area_path` from all JSONs to build VALID_AREAS
- **workstream.py:** Creates infrastructure (area path, folder, slice template)

---

## Creating or Changing Workstreams

For creating new workstreams, read `system/skills/create-workstream/SKILL.md`.

For restructuring (promotions, demotions, consolidations), the steps are:

1. Update JSON files in `identity/workstreams/`
2. Move/rename folders if needed
3. Update or delete slice files in `identity/slices/`
4. Create, rename, or move AZ DevOps area paths
5. Move affected work items to new area paths
6. Update CLAUDE.md if boot instructions reference old names
7. Run synthesis to capture new state
