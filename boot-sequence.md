# Boot Sequence

**Version:** 5.0

This file is the universal boot protocol. Any AI, any platform, follows these steps.
All paths and configuration come from `identity/boot.json` and
`identity/personalities/*/personality.json`. Do not hardcode paths. Read them from the JSON.

## Step 1: Read Boot Configuration

Read `identity/boot.json`. This file defines what to load and where things live.

## Step 2: Load Common Context

For each file in `common_files` from boot.json, read it in full. If your tools truncate, read the remaining lines.

Then:
- Run `git log --oneline -{git_log_depth}` (depth from boot.json)
- If `work_items.enabled` is true, write the PAT to `{work_items.pat_file}` and run `python3 {work_items.script} list`

PAT source is platform-specific:
- Claude Projects: PAT is in project instructions (already in your context)
- Local LLM: PAT from environment variables
- MCP: PAT is in the server's user database

## Step 3: Determine Personality

Read all `personality.json` files in `{personality_directory}/*/` (path from boot.json).

If the first message specifies a focus (e.g., "This is Ops V16"), load that personality.
Otherwise, match the first message against each personality's `trigger_words` array.
If no trigger words match, use `{default_personality}` from boot.json.

## Step 4: Load Personality Context

From the matched personality's personality.json:

1. Read `behavior.md` in the same folder as personality.json
2. Read each file in `boot_files`
3. Read all files in each directory in `boot_directories`
4. Set git identity from `git_identity`:
   ```
   git config user.name "{name}"
   git config user.email "{email}"
   ```
5. Note `resources` and `wiki_pages` as available on-demand references. Do NOT load these at boot. When a topic matches a resource keyword, read the paths listed.

## Step 5: Boot Verification

List what you read and confirm readiness. Example:
```
Boot complete (Ops personality):
- identity-rules.md: 140 lines (full)
- status.md: 208 lines (full)
- ops/behavior.md: 35 lines (full)
- git log: 20 commits
- AZ DevOps: 36 items
- Resources available: linkedin, career, articles, ideas
```
