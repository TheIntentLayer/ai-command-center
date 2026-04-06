// Claude Synthesizer v2 -- Prompt templates
// Exposes window.SynthPrompts for use by orchestrator.js.
// Loaded via manifest before orchestrator.js.
//
// The synthesis slice (identity/slices/synthesis/slice.md) carries the
// ground rules: timezone, judgment guidance, what to include vs not,
// writing rules. These prompts carry the operational instructions that
// need to be fresh in context when used: the 6-category extraction
// framework (repeated per chat) and the STATE.md format (sent at end).
//
// Placeholders filled at runtime by the orchestrator:
//   {chat_name}   -- name of the chat being processed
//   {chat_num}    -- position in sequence (1, 2, 3...)
//   {chat_count}  -- total number of chats
//   {chat_list}   -- comma-separated list of all chat names
//   {transcript}  -- full chat transcript in [USER]/[THINKING]/[CLAUDE] format
//   {timestamp}   -- current date/time in user's timezone (filled by orchestrator)
//   {timezone}    -- user's timezone name (e.g., "America/Los_Angeles")
(function () {
  'use strict';

  window.SynthPrompts = {

    // -----------------------------------------------------------------------
    // Boot message for the temp synthesis chat
    // -----------------------------------------------------------------------
    boot: `\
This chat will be named "Exclude for synthesis". It will be used for \
synthesizing purposes. You will receive transcripts from {chat_count} \
chats: {chat_list}. When your boot is complete, respond with exactly \
this as your final line: BOOT COMPLETE`,

    // -----------------------------------------------------------------------
    // Supplements: gather detailed git + AZ data before chat analysis
    // -----------------------------------------------------------------------
    supplements: `\
Before processing chat transcripts, gather detailed supplementary data. \
Run these commands and note the output:

1. git log --all --since='7 days ago' --format='%ai %an | %s' \
--grep='Persist auto-backup' --grep='Synthesis step' \
--grep='STATE.md synthesized' --invert-grep
2. python3 system/scripts/az_ops.py list
3. python3 system/scripts/az_ops.py list --all
4. Read identity/core.md for reference

Your final line MUST be exactly: SUPPLEMENTS COMPLETE`,

    // -----------------------------------------------------------------------
    // Per-chat extraction (sent once per chat with full transcript)
    // -----------------------------------------------------------------------
    extraction: `\
Chat {chat_num} of {chat_count}: {chat_name}

Extract findings in these categories:

### 1. What Happened
Work completed. Files created, renamed, moved, deleted. Code committed. \
Documents produced. Communications sent outside this project (emails, \
messages, form submissions). Subscriptions changed. Work items opened \
or closed.

### 2. What Was Decided
Choices that should not be re-opened. New rules or conventions established. \
Naming decisions. Architectural decisions. Things explicitly rejected or \
ruled out, and why. If a decision changed during the session, capture the \
final answer and note it changed.

### 3. What's In Progress
Work started but not finished. Things blocked or waiting on someone \
(name the person or entity). Questions asked but not answered. \
Investigations concluded with "not yet, but later."

### 4. What's Next
Commitments for specific future actions ("I'll do X tomorrow", \
"we need to do Y"). Deadlines mentioned. Priority changes or reordering. \
Anything the person said they would do after the session ended.

### 5. How the Partnership Is Working
- Corrections: specific corrections the person made to AI behavior. \
What triggered each. Whether it became a standing rule.
- Communication breakdowns: moments where the AI misunderstood, rushed \
ahead, gave bad advice, or caused friction. What resolved it.
- Emotional arc: track the person's energy across the session. Where did \
they start? What shifted their mood? Where did they end?
- What worked well: genuine partnership moments, breakthroughs.

### 6. What Connects Across Chats
References to work in other chats. Information that crossed chat boundaries. \
Governance corrections that apply to all chats. If you have already \
processed earlier chats in this session, note connections to those findings.

## Rules
- No hallucinations. No assumptions. Only include what you can verify \
from the transcript.
- If a category has nothing, say "Nothing found" explicitly.
- Include exact quotes where they reveal tone or a correction that \
paraphrasing would soften.
- Be thorough. What you miss, the next instance will never know existed.
- Pay special attention to the END of the conversation.

Your final line MUST be exactly:
ANALYSIS COMPLETE: {chat_name}

---

{transcript}`,

    // -----------------------------------------------------------------------
    // Final synthesis (sent after all chats are processed)
    // -----------------------------------------------------------------------
    synthesis: `\
All {chat_count} chats have been processed: {chat_list}.

You have the supplementary data (git log, AZ DevOps board, core.md) \
from earlier in this conversation. You have the chat analyses from \
all {chat_count} transcripts. Now produce STATE.md.

You are producing a STATE.md document -- the "State of the Union" for \
this AI partnership project. This is not a summary. STATE.md tells a \
new partner where we are across everything, what we are thinking, what \
matters right now, and what to do next. A brand-new AI instance with \
zero memory of these conversations will rely on STATE.md to resume as \
a partner on the very first message.

TIMEZONE: All dates and times in STATE.md must be in the user's \
local timezone ({timezone}). When you write deadlines, "last active" \
timestamps, or day-of-week labels, use this timezone.

PREDECESSOR DETECTION: Multiple chats may be versions of the same \
workstream (e.g., "Ops V14", "Ops V15"). Only include the latest \
active version. Determine "latest" by the most recent human message \
timestamp, not by version number alone. Also detect predecessor \
relationships by name similarity, not just version numbers.

WHAT THE NEW CHAT WILL ALREADY HAVE: The new chat's boot sequence \
(CLAUDE.md) will instruct it to read STATE.md, identity/core.md, \
personality slice definitions, AZ DevOps work items, and git log. \
DO NOT DUPLICATE information that already lives in those files. \
Extract only what would be LOST if these conversations disappeared.

Specifically:
- Do NOT describe who the human is (core.md covers this)
- Do NOT list all active issues (the board covers this)
- DO capture decisions and new rules established during these sessions
- DO capture in-flight work that issue titles alone cannot convey
- DO capture the human's current thinking, priorities, and emotional state
- DO capture unfinished threads, half-formed ideas, and open questions
- DO capture implicit commitments ("I'll do X tomorrow", "let me check with Y")

JUDGMENT GUIDANCE:
- When in doubt, include. The cost of a false inclusion is low. The \
cost of a false exclusion is a broken cold start.
- Mark inferred items with [inferred] so the new chat can calibrate trust.
- Pay attention to the END of each conversation. That is where current \
state lives.
- Pay attention to tone shifts. Frustration, excitement, direction \
changes are all signal.
- Look for implicit commitments across chats. One chat may reference \
work happening in another.

Write STATE.md to identity/state/STATE.md using the structure below. \
Every section is required. If a section has no content, write \
"None this session."

Start with EXACTLY these lines:

# STATE.md

## Generated: {timestamp}
## Source: In-project synthesis (DOM export + git + board)
## Generated by: Synthesizer v2

---

## The Union

### Architecture
Current system architecture. What version of the personality system \
is active. How many slices. How the synthesis pipeline works. Keep \
this brief -- it changes rarely.

### Active Workstreams
For each active workstream: current status, key facts, what is open, \
what is blocked. This is the single section a new chat reads to \
understand what is happening across the entire project. Be thorough here.

### Deadlines This Week and Coming
Table of upcoming deadlines with dates and status.

### Decisions Made This Cycle
Numbered list of decisions from the chat extractions. These are \
choices that should not be re-opened.

### New Rules Established This Cycle
Rules or conventions established during these sessions that affect \
future behavior.

### Recent Commits (Key)
Notable commits from git log. Not every commit -- the ones that \
matter for context.

---

## Session: [Chat Name] (last active: [timestamp in PT])

For each CURRENT chat (not predecessors), what was being discussed. \
Where it stopped. Current thinking. Open threads. Emotional context. \
Everything that would be lost if this chat disappeared.

Repeat this section for each active chat. Preserve the identity and \
voice of each session. Each workstream has its own tone and focus. Do not \
blend them.

## Session: Claude Code (last activity: [timestamp in PT])

Built from git commits. What was implemented, what was tested, what \
is next. Not conversational context -- implementation context.

## Where to Pick Up

Unified across all sessions. The single most important next action, \
then the next 3-5. Prioritize across chats, not within each one. \
Be specific: not "continue V3 work" but "test X, then do Y."

## Writing Rules

- No em dashes anywhere. Use -- (double hyphen) instead.
- No bold in prose. Bold only in headers and labels.
- Write in direct, clear language. The voice of a trusted colleague \
handing off to the next shift.
- Cross-chat references: when one chat says "Claude Code built the \
synthesizer today," connect it to the Claude Code section. Do not \
repeat the same fact in multiple sections.
- Emotional context: consolidate in the most relevant chat section. \
Do not repeat across all sections.
- Length: for 2-3 active chats + Claude Code, target 2,000-4,000 \
words. Quality over compression.

## Commit Instructions

Commit STATE.md with message: "STATE.md synthesized from DOM export + git + board"

After the commit succeeds, your FINAL line MUST be exactly:
COMMIT SYNTHESIS: [hash]
where [hash] is the actual git commit hash.`,

  };
})();
