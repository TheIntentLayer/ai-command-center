# Skill: Create a Personality

**Version:** V5.0
**When to use:** Adding a new personality to an existing AI Command Center.

---

## Prerequisites

- An existing AI Command Center repo with `identity/` folder, `boot-sequence.md`, and at least one personality already set up.
- Know the focus area (what this personality handles).
- Know which files it needs at boot vs on-demand.

---

## Steps

### 1. Create the personality folder

```bash
mkdir -p identity/personalities/{name}
```

Use lowercase, hyphenated names: `ops`, `book`, `consulting`, `research-lab`.

### 2. Create personality.json

Create `identity/personalities/{name}/personality.json` with this exact schema:

```json
{
  "name": "Display Name",
  "description": "One-line description of what this personality handles.",
  "area_path": "AreaPathName",
  "folder": "root-level-content-folder-or-null",
  "trigger_words": ["word1", "word2", "phrase three"],
  "git_identity": {
    "name": "Claude-PersonalityName",
    "email": "claude-personalityname@yourdomain.dev"
  },
  "boot_files": [
    "path/to/file1.md",
    "path/to/file2.md"
  ],
  "boot_directories": [
    "path/to/directory"
  ],
  "resources": {
    "keyword": {
      "paths": ["path/to/resource/"],
      "description": "When to use this resource"
    }
  },
  "wiki_pages": {
    "keyword": "Wiki-Page-Name"
  },
  "active": true,
  "created": "YYYY-MM-DD"
}
```

**Field reference:**

| Field | Required | Description |
|-------|----------|-------------|
| name | yes | Display name shown in boot verification |
| description | yes | One-line summary of personality focus |
| area_path | yes | AZ DevOps area path for work items. null if no tracking. |
| folder | no | Root-level content folder (e.g., "book", "consulting"). null if none. |
| trigger_words | yes | Array of words/phrases that match this personality during boot. |
| git_identity | yes | Name and email for git commits in this personality. |
| boot_files | yes | Array of file paths loaded at every boot. Can be empty []. |
| boot_directories | yes | Array of directory paths. All .md files inside are loaded at boot. Can be empty []. |
| resources | yes | Keyword-mapped on-demand references. NOT loaded at boot. Can be empty {}. |
| wiki_pages | yes | Keyword-mapped wiki page names. Can be empty {}. |
| active | yes | true or false. Inactive personalities are ignored during boot. |
| created | yes | Date personality was created (YYYY-MM-DD). |

### 3. Create behavior.md

Create `identity/personalities/{name}/behavior.md` with behavioral prose. This file contains:

- Focus and system declaration
- Behavioral rules that extend identity-rules.md
- Domain-specific context, key people, tone guidance
- Session discipline rules (if any)

**Do NOT include:**
- File lists (those are in personality.json boot_files/boot_directories)
- Git configuration (that is in personality.json git_identity)
- On-demand resource references (those are in personality.json resources)

behavior.md is pure behavioral prose. No configuration.

### 4. Register the area path (if new)

If the personality uses a new area_path not already in `identity/tracking/areas.json`, add it:

```json
{
  "name": "NewArea",
  "handled_by": "personality-name",
  "description": "What this area covers"
}
```

### 5. Verify boot

Start a new chat. The boot sequence should:
1. Find the new personality.json during Step 2 (personality matching)
2. Match trigger words from the first message
3. Load behavior.md + all boot_files + all files in boot_directories
4. Set git identity
5. Show the new personality in boot verification

### 6. Commit

```bash
git add identity/personalities/{name}/
git commit -m "Add {name} personality

Focus: {description}
Boot files: {count}
Area path: {area_path}"
```

---

## Promoting from Tracking Area to Personality

If a topic currently lives as a tracking area in `identity/tracking/areas.json` and needs its own behavioral context:

1. Follow Steps 1-4 above to create the personality.
2. Update `identity/tracking/areas.json`: change the area's `handled_by` from the old personality to the new one.
3. Move any content files from the old personality's folder to the new personality's content folder (if applicable).
4. The promotion is complete when the new personality can boot independently and the tracking area routes to it.

---

## Common Mistakes

- Putting file references in behavior.md instead of personality.json. If code needs to read it, it goes in JSON.
- Forgetting to add boot_files as an empty array []. All fields are required, even if empty.
- Using the same trigger words as another personality. Check existing personality.json files for conflicts.
- Creating a personality for something that should be a tracking area. Personalities need distinct behavioral rules. If the behavior is the same as an existing personality, use a tracking area instead.
