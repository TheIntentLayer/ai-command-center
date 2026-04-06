# CLAUDE.md

## Boot Sequence

**Last Updated:** {DATE} (V4.4)

### Step 1: L1 (Universal, every chat)

Read these in order. Read every file in full. If the `view` tool truncates, read the remaining lines.

1. **`identity/identity-rules.md`** - WHO the human is. Universal identity, behavioral rules, working style. Always loaded.
2. **`identity/state/status.md`** - WHERE everything stands. Current snapshot, all active work, deadlines, session stopping points. Always loaded.
3. **`git log --oneline -20`** - WHAT changed recently.
4. **Azure DevOps** - Write PAT to token file once (all scripts read from it automatically):
   ```
   echo "[AZ DevOps PAT from project instructions]" > ~/azure-dev-ops-claude-token.txt
   python3 system/scripts/az_ops.py list
   ```

### Step 2: Determine Personality

If the first message specifies a focus (e.g., "This is Ops V1"), load that personality.

If not, ask: **"What's the focus of this chat?"**

**Personality registry:** Read all `personality.json` files in `identity/personalities/*/`. For each file with `"active": true`, match the first message against the `trigger_words` array. Load the `behavior-rules-and-context.md` from the same folder.

If no trigger words match, default to the Ops personality (`identity/personalities/ops/behavior-rules-and-context.md`).

### Step 3: Load Personality Context

Read the personality's `behavior-rules-and-context.md`. It tells you what additional files and wiki pages to load for that personality.

### Step 4: Boot Verification

List what you read and confirm readiness. Example:
```
Boot complete (Ops personality):
- identity-rules.md: 98 lines (full)
- status.md: 45 lines (full)
- ops/behavior-rules-and-context.md: 28 lines (full)
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

Other personalities may specify their own git identity in their behavior-rules-and-context.md.

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
- `system/skills/create-personality/SKILL.md` -- creating personalities or tracking areas

---

## State Management

1. **Synthesizer v2** (Chrome extension) produces status.md via DOM export + in-project synthesis. Click "Synthesize" in the extension popup. Run daily at end of last session.
2. **Daily logs** live in AZ DevOps (tagged `daily-log`). Ask Claude to "update the daily log" at end of session.

If status.md seems stale, check `git log identity/state/status.md` for when it was last updated.
