# CLAUDE.md

## Boot Sequence

**Last Updated:** {DATE}

### Step 1: L1 (Universal, every chat)

Read these in order. Read every file in full. If the `view` tool truncates, read the remaining lines.

1. **`identity/core.md`** - WHO the human is. Universal identity, behavioral rules, working style. Always loaded.
2. **`identity/state/STATE.md`** - WHERE everything stands. Current snapshot, all workstreams, deadlines, session stopping points. Always loaded.
3. **`git log --oneline -20`** - WHAT changed recently.
4. **Azure DevOps** - Write PAT to token file once (all scripts read from it automatically):
   ```
   echo "[AZ DevOps PAT from project instructions]" > ~/azure-dev-ops-claude-token.txt
   python3 system/scripts/az_ops.py list
   ```

### Step 2: Determine Personality Slice

If the first message specifies a focus (e.g., "This is Ops V1"), load that slice.

If not, ask: **"What's the focus of this chat?"**

**Slice registry:** Read all `.json` files in `identity/workstreams/`. For each file with `"tier": 1` and `"active": true`, match the first message against the `trigger_words` array. Load the slice file specified in the `slice` field.

If no trigger words match, default to the Ops slice (`identity/slices/ops/slice.md`).

**Conceptual model:** For how workstreams, tiers, slices, and area paths relate, read `system/docs/workstream-architecture-v4.3.md`.

### Step 3: Load Slice Context

Read the slice's `slice.md`. It tells you what additional files and wiki pages to load for that personality.

### Step 4: Boot Verification

List what you read and confirm readiness. Example:
```
Boot complete (Ops slice):
- core.md: 98 lines (full)
- STATE.md: 45 lines (full)
- ops/slice.md: 28 lines (full)
- git log: 20 commits
- AZ DevOps: 12 items
```

---

## Git Configuration

Set at start of every engagement:
```
git config user.name "{DEFAULT_GIT_NAME}"
git config user.email "{DEFAULT_GIT_EMAIL}"
```

Other slices may specify their own git identity in their slice.md.

---

## PATs

PATs are provided via project instructions. They are automatically available in every chat's context window.

- **GitHub Classic PAT:** Scopes: repo, workflow, read:org, project, gist.
- **AZ DevOps PAT:** Scopes: Work Items, Project and Team, Wiki, Dashboard, Task Groups.

Do not ask for PATs. Do not expect them in the first message. They are already in your context from project instructions.

---

## Skills

`system/skills/` contains documented procedures for operations you may not be familiar with. **Read the relevant SKILL.md before attempting an unfamiliar operation.** Skills are not loaded at boot. Read them on demand when you need them.

Available skills:
- `system/skills/create-workstream/SKILL.md` -- creating or promoting workstreams

---

## State Management

1. **Synthesizer v2** (Chrome extension) produces STATE.md via DOM export + in-project synthesis. Click "Synthesize" in the extension popup. Run daily at end of last session.
2. **Daily logs** live in AZ DevOps (tagged `daily-log`). Ask Claude to "update the daily log" at end of session.

If STATE.md seems stale, check `git log identity/state/STATE.md` for when it was last updated.
