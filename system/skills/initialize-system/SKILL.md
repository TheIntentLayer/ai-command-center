# Skill: Initialize an AI Command Center

**Version:** V5.0
**When to use:** Setting up a new AI Command Center from scratch for a new user.

---

## What You Are Building

An AI Command Center is a git repo that gives any AI (Claude, Copilot, ChatGPT, local models) persistent context about who the human is, how they work, and what is happening. The AI boots from this repo and operates as a partner, not a blank slate.

---

## Folder Structure

Create this structure:

```
repo-root/
  boot-sequence.md          # Universal boot protocol (any AI follows this)
  CLAUDE.md                  # 1-liner wrapper (Claude Code convention)
  identity/
    boot.json                # SST for common boot config (what to load)
    identity-rules.md        # WHO: universal identity and behavioral rules
    state/
      status.md              # WHERE: current state across everything
    personalities/
      ops/
        personality.json     # Structured config for this personality
        behavior.md          # Behavioral prose for this personality
    tracking/
      areas.json             # Tracking categories for work items
  system/
    scripts/                 # Automation scripts (az_ops.py, etc.)
    skills/                  # Documented procedures
    docs/                    # Design docs, version history
```

---

## Step 1: Create the repo

```bash
mkdir my-command-center && cd my-command-center
git init
mkdir -p identity/state identity/personalities/ops identity/tracking system/scripts system/skills system/docs
```


---

## Step 1a: Create identity/boot.json

This is the single source of truth for common boot configuration. Both boot-sequence.md and MCP load_context() read from this file.

```json
{
  "version": "5.0",
  "common_files": [
    "identity/identity-rules.md",
    "identity/state/status.md"
  ],
  "personality_directory": "identity/personalities",
  "default_personality": "ops",
  "git_log_depth": 20,
  "work_items": {
    "enabled": true,
    "script": "system/scripts/az_ops.py",
    "pat_file": "~/azure-dev-ops-claude-token.txt"
  }
}
```

---

## Step 2: Create boot-sequence.md

This is the universal boot protocol. Any AI follows it.

```markdown
# Boot Sequence

All paths come from `identity/boot.json` and `identity/personalities/*/personality.json`.

## Step 1: Read `identity/boot.json`

## Step 2: Load Common Context

Read each file in `common_files` from boot.json. Then:
- `git log --oneline -{git_log_depth}`
- If `work_items.enabled`, run `python3 {work_items.script} list`

## Step 3: Determine Personality

Read all `personality.json` files in `{personality_directory}/*/` from boot.json.
Match the first message against `trigger_words`. If no match, use `{default_personality}`.

## Step 4: Load Personality Context

1. Read the matched personality's **behavior.md**.
2. Read each file in `boot_files` from personality.json.
3. Read all files in each directory in `boot_directories` from personality.json.
4. Set git identity from `git_identity` in personality.json.
5. Note `resources` and `wiki_pages` as on-demand references (do NOT load at boot).

## Step 5: Boot Verification

List what you read and confirm readiness.
```

---

## Step 3: Create CLAUDE.md

```markdown
# CLAUDE.md

Read and follow boot-sequence.md
```

Two lines. Exists because Claude Code looks for this filename by convention.

---

## Step 4: Create identity-rules.md

This is the central document. It defines who the human is, how the AI should operate, and hard rules that apply to every conversation regardless of personality.

Sections to include:

1. **Who I Am** -- name, role, location, current phase of work, family context
2. **How I Work** -- working style, communication preferences, schedule patterns
3. **How the AI Should Operate** -- behavioral expectations (be direct, push back, track everything, etc.)
4. **Hard Rules** -- non-negotiable constraints (style rules, confidentiality, framing rules)
5. **System Coordination** -- how multiple AI instances coordinate (work items, status.md, daily logs)
6. **Operational Rules** -- git workflow, wiki access, skills, state management
7. **Personalities Architecture** -- explanation of how personalities work

Write in first person where it helps. This document is read by the AI about the human. Use present tense. Be specific. Vague rules get ignored.

---

## Step 5: Create status.md

Start with a minimal status file:

```markdown
# Status

**Last Updated:** [date]

## Active Work

No active work items yet. This file will be updated as work progresses.
```

status.md grows over time. It is the living snapshot of where everything stands. Updated by the Synthesizer or manually.

---

## Step 6: Create the first personality (Ops)

Every system needs at least one personality. Start with Ops (general-purpose).

### identity/personalities/ops/personality.json

```json
{
  "name": "Ops",
  "description": "General operations, system management, and default personality.",
  "area_path": "System",
  "folder": null,
  "trigger_words": ["ops", "system", "general"],
  "git_identity": {
    "name": "AI-Ops",
    "email": "ai-ops@yourdomain.dev"
  },
  "boot_files": [],
  "boot_directories": [],
  "resources": {},
  "wiki_pages": {},
  "active": true,
  "created": "YYYY-MM-DD"
}
```

### identity/personalities/ops/behavior.md

```markdown
# Personality: Ops

**Focus:** General operations, system management, project oversight.
**System:** You are the Ops personality, the default general-purpose personality.

---

## Behavioral Rules (extends identity-rules.md)

- One thing at a time. Think before acting.
- Track all decisions and work items.
```

Start minimal. Add rules as patterns emerge from real conversations.

---

## Step 7: Create areas.json

```json
[
  {
    "name": "System",
    "handled_by": "ops",
    "description": "System infrastructure, deployment, operational tasks"
  }
]
```

Add more areas as work diversifies.

---

## Step 8: Initial commit

```bash
git add -A
git commit -m "Initialize AI Command Center (V5.0)

Structure: boot.json, boot-sequence.md, identity-rules.md, status.md, ops personality.
Ready for first conversation."
```

Push to GitHub (or keep local for local LLM use).

---

## Step 9: Connect to an AI platform

### Claude Projects (claude.ai)
Set project instructions to:
```
Repo: github.com/youruser/your-repo
Classic PAT: [your-pat]
On first message, clone the repo and follow CLAUDE.md.
```

### MCP Server
Deploy the AI Command Center MCP server (github.com/TheIntentLayer/ai-command-center-mcp) and connect it to your preferred MCP client.

### Copilot Studio (M365 Copilot Chat)
Create a Copilot Studio agent, add the MCP server URL as a tool (Model Context Protocol type), and publish to M365 Copilot. See `system/docs/mcp/copilot-studio-integration.md` for the verified path.

### Local LLM
Clone the repo locally. Point your local model at boot-sequence.md. Provide PATs via environment variables.

---

## What Comes Next

1. **Add more personalities** as your work diversifies. See `system/skills/create-personality/SKILL.md`.
2. **Set up the Synthesizer** to automatically produce status.md from conversation history.
3. **Add resources and wiki_pages** to personality.json as on-demand reference folders accumulate.
4. **Add boot_files** when you create documents that should load with every conversation in a personality.
5. **Grow identity-rules.md** as you discover rules that apply across all personalities.

Start small. Let the system grow from real usage, not upfront planning.
