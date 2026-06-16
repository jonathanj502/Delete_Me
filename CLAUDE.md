# CLAUDE.md

## Scratchpad Protocol

Maintain `.claude/scratchpad.md` as an append-only milestone log throughout every session.

**When to append** — one line per event, immediately when it occurs:
- A test passes or a "Testable" criterion from PLAN.md is met → `[PASS]`
- A subtask or implementation chunk is fully complete → `[PASS]`
- A concrete, task-scoped decision is made → `[DECISION]`
- An approach fails and must not be retried → `[FAIL]`
- A path is intentionally skipped → `[SKIP]`

**Line format:**
```
[STATUS] Description — file:line or chunk name (YYYY-MM-DD HH:MM)
```

**Rules:**
- Append only. Never edit or delete past entries.
- One event per line. Do not batch milestones.
- Descriptions are factual: what happened, not what was planned.
- Do not write behavioral guidelines or architectural principles here — those belong in CLAUDE.md itself.

## Session Start Protocol

At the start of every session, and after any context compaction:
1. If `HANDOVER.md` exists at the project root, read it first
2. Re-read `.claude/scratchpad.md`
3. Find the most recent `## SESSION END` divider; consider only entries after it
4. Treat every `[FAIL]` entry as a blocked path — do not retry without explicit user instruction

## Handoff Reminder

When the conversation has grown long or complex, proactively suggest:
`"Consider running /user:handoff before we continue to save session state."`

## Notes

- `HANDOVER.md` is a generated snapshot file. It is gitignored and should never be committed.
- The scratchpad is persistent project state and should remain in version control.
