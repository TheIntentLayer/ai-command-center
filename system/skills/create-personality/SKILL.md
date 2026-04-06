# Skill: Create Personality

**When to use:** The human asks to create, add, or convert something into a personality or tracking area. Phrases like "let's create a personality for X", "I think X needs its own mode", "convert X to a personality", "X is becoming a real thing", "track X under Ops."

**Registry:** `identity/personalities/*/personality.json` and `identity/tracking/areas.json`
**Utility:** `python3 system/scripts/personality.py`

---

## Step 1: Determine What to Create

Before asking questions, assess what you already know. If you have context from the conversation or from project files, use it. Don't ask questions you can answer yourself.

**Personality:** Gets its own chat sessions, behavioral rules, dedicated folder, AZ area path.
- Needs a different thinking mode than existing personalities
- Has or will have dedicated files and documents
- Warrants its own chat (e.g., "Book V4")
- Has recurring work with distinct behavioral rules

**Tracking Area:** AZ area path and folder for organization, but handled by an existing personality (usually Ops).
- Has files and work items but doesn't need its own thinking mode
- Work happens inside an existing personality's chat
- Examples: Articles, LinkedIn, Career, Personal

**Idea:** Not yet tracked. Lives in ideas/ folder.
- Just captured, no infrastructure needed
- Might become a tracking area or personality later when it accumulates gravity

**Decision signals:**
- "I need a chat for this" -> Personality
- "I need to track this but I handle it in Ops" -> Tracking Area
- "Just capture this thought" -> Idea (use ideas/ folder, no creation needed)

If ambiguous, ask: "Does X need its own chat with its own behavioral rules, or is it work you handle in [existing personality]?"

---

## Step 2: Gather Details

For **obvious cases** (you have enough context):
- Confirm name and type, and propose the JSON
- "Based on what I know about the Book work, here's what I'd create. Look right?"

For **ambiguous cases**, ask only what you need:
- "What should we call it?" (name)
- "What words should trigger this personality?" (trigger_words, personality only)
- "Does it have a folder already, or should I create one?" (folder)
- "What git identity should commits use?" (git_identity, or default to Claude-Ops)

For **promotions** (idea -> tracking area, or tracking area -> personality):
- Check if the ideas/ file or existing folder has content to carry forward

**Do not ask:**
- Area path name (derive from the name)
- Behavior file path (follows convention: `identity/personalities/{name}/behavior-rules-and-context.md`)
- Whether it needs an AZ area (yes, always for personalities and tracking areas)

---

## Step 3: Create the Definition

### For a Personality

Create a folder in `identity/personalities/{name}/` with a `personality.json`:

```json
{
  "name": "Display Name",
  "description": "One-line description.",
  "area_path": "AreaPathName",
  "folder": "folder-name",
  "trigger_words": ["word1", "word2", "word3"],
  "git_identity": { "name": "Claude-Research", "email": "{YOUR_EMAIL}" },
  "active": true,
  "created": "YYYY-MM-DD"
}
```

### For a Tracking Area

Add an entry to `identity/tracking/areas.json`:

```json
{
  "name": "Display Name",
  "area_path": "AreaPathName",
  "folder": "folder-name",
  "handled_by": "ops",
  "description": "One-line description."
}
```

---

## Step 4: Run the Utility (Personality only)

```bash
python3 system/scripts/personality.py create identity/personalities/{name}/personality.json
```

This creates:
- AZ DevOps area path (API call)
- Root folder with .gitkeep (if it doesn't exist)
- behavior-rules-and-context.md from template

It does NOT need to update CLAUDE.md, identity-rules.md, or az_ops.py. Those read from the registry dynamically.

For tracking areas, you only need to:
1. Add the entry to areas.json
2. Create the AZ area path: `python3 system/scripts/az_ops.py create-area "AreaName"`
3. Create the folder with .gitkeep if needed

---

## Step 5: Commit

```bash
git add -A
git commit -m "Personality created: {name}"
git push origin main
```

---

## Step 6: Verify

```bash
python3 system/scripts/personality.py list
python3 system/scripts/personality.py sync-check
```

Confirm the new personality appears in the list and sync-check shows no issues.

---

## Edge Cases

**Overlaps with existing personality:** Suggest expanding the existing personality before creating a new one. "This sounds like it fits inside your Ops personality. Should we add trigger words there instead of creating a new one?"

**Sub-project within existing personality:** If the work is a project within an existing personality (e.g., "SubProject-A" within Workstream-1), it doesn't need its own personality. It needs a subfolder and maybe an AZ area tag, not a new thinking mode.

**Renaming a personality:** Create the new personality folder with the correct name. Deactivate the old one. Move the folder if needed. Update the behavior-rules-and-context.md. The registry handles the rest.

**Deactivating a personality:** Run `personality.py deactivate identity/personalities/{name}/personality.json`. This sets active:false. The behavior file and folder are preserved. CLAUDE.md, identity-rules.md, az_ops.py stop showing it at next boot.

---

## Common Git Identities

| Identity | Use for |
|----------|---------|
| Claude-Ops | General ops, system, consulting |
| Claude-Book | Book writing |
| Claude-Research | AI Trust Commons, governance, architecture research |
| Synthesizer-Ops | Synthesis pipeline only |
