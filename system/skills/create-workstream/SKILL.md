# Skill: Create Workstream

**When to use:** The human asks to create, add, or convert something into a workstream. Phrases like "let's create a workstream for X", "I think X needs its own slice", "convert X to a workstream", "X is becoming a real thing."

**Registry:** `identity/workstreams/*.json`
**Utility:** `python3 system/scripts/workstream.py`

---

## Step 1: Determine the Tier

Before asking questions, assess what you already know. If you have context from the conversation or from project files, use it. Don't ask questions you can answer yourself.

**Tier 1 (Full Workstream):** Gets its own chat sessions, slice with behavioral rules, dedicated folder, AZ area path.
- Needs a different thinking mode than existing slices
- Has or will have dedicated files and documents
- Warrants its own chat (e.g., "Book V4")
- Has recurring work with distinct behavioral rules

**Tier 2 (Tracked Category):** AZ area path and folder for organization, but handled by an existing slice (usually Ops).
- Has files and work items but doesn't need its own thinking mode
- Work happens inside an existing slice's chat
- Examples: Articles, LinkedIn, Career, Personal

**Tier 3 (Idea):** Not yet a workstream. Lives in ideas/ folder.
- Just captured, no infrastructure needed
- Might become a workstream later when it accumulates gravity

**Decision signals:**
- "I need a chat for this" -> Tier 1
- "I need to track this but I handle it in Ops" -> Tier 2
- "Just capture this thought" -> Tier 3 (use ideas/ folder, no workstream creation needed)

If ambiguous, ask: "Does X need its own chat with its own behavioral rules, or is it work you handle in [existing slice]?"

---

## Step 2: Gather Details

For **obvious cases** (you have enough context):
- Confirm name, tier, and propose the JSON
- "Based on what I know about the Book workstream, here's what I'd create. Look right?"

For **ambiguous cases**, ask only what you need:
- "What should we call it?" (name)
- "What words should trigger this slice?" (trigger_words, Tier 1 only)
- "Does it have a folder already, or should I create one?" (folder)
- "What git identity should commits use?" (git_identity, or default to Claude-Ops)

For **promotions** (idea -> Tier 2, or Tier 2 -> Tier 1):
- Check if the ideas/ file or existing folder has content to carry forward
- The JSON captures the history: `"created"` date is when it became this tier

**Do not ask:**
- Area path name (derive from the workstream name)
- Slice path (follows convention: `identity/slices/{name}/slice.md`)
- Whether it needs an AZ area (yes, always for Tier 1 and 2)

---

## Step 3: Create the JSON

Write the JSON file to `identity/workstreams/{name}.json`.

Schema:
```json
{
  "name": "Display Name",
  "tier": 1,
  "area_path": "AreaPathName",
  "folder": "folder-name",
  "slice": "identity/slices/folder-name/slice.md",
  "trigger_words": ["word1", "word2", "word3"],
  "git_identity": { "name": "Claude-Research", "email": "{YOUR_EMAIL}" },
  "handled_by": null,
  "active": true,
  "created": "YYYY-MM-DD",
  "description": "One-line description."
}
```

For Tier 2: `slice`, `trigger_words`, and `git_identity` are null. Set `handled_by` to the slice that handles this work (usually "ops").

---

## Step 4: Run the Utility

```bash
python3 system/scripts/workstream.py create identity/workstreams/{name}.json
```

This creates:
- AZ DevOps area path (API call)
- Root folder with .gitkeep (if it doesn't exist)
- Slice.md from template (Tier 1 only)

It does NOT need to update CLAUDE.md, core.md, or az_ops.py. Those read from the registry dynamically.

---

## Step 5: Commit

```bash
git add -A
git commit -m "Workstream created: {name} (Tier {tier})"
git push origin main
```

---

## Step 6: Verify

```bash
python3 system/scripts/workstream.py list
python3 system/scripts/workstream.py sync-check
```

Confirm the new workstream appears in the list and sync-check shows no issues.

---

## Edge Cases

**Workstream overlaps with existing slice:** Suggest expanding the existing slice before creating a new one. "This sounds like it fits inside your Ops slice. Should we add trigger words there instead of creating a new one?"

**Workstream is a sub-project:** If the work is a project within an existing workstream (e.g., "SubProject-A" within Workstream-1), it doesn't need its own workstream. It needs a subfolder and maybe an AZ area tag, not a new slice.

**Renaming a workstream:** Create the new JSON with the correct name. Deactivate the old one. Move the folder if needed. Update the slice.md. The registry handles the rest.

**Deactivating a workstream:** Run `workstream.py deactivate identity/workstreams/{name}.json`. This sets active:false. The slice file and folder are preserved. CLAUDE.md, core.md, and az_ops.py stop showing it at next boot.

---

## Common Git Identities

| Identity | Use for |
|----------|---------|
| Claude-Ops | General ops, system, consulting |
| Claude-Book | Book writing |
| Claude-Research | AI Trust Commons, governance, architecture research |
| Synthesizer-Ops | Synthesis pipeline only |
