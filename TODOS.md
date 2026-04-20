# TODOS

## launchd auto-start for english-coach server

**What:** A macOS launchd agent that starts `server.py` on login and restarts it if it crashes.

**Why:** Without auto-start, the user must run `python server.py` before every Claude Code session. If they forget, all corrections are silently lost. A tool that claims "zero extra effort" can't require a manual startup step every day.

**Pros:** Corrections always available. No manual steps. Survives reboots.

**Cons:** Fiddly to configure. Harder to debug (system log). One more thing to set up at install time.

**Context:** This is the single biggest operational pain point post-v1. If you find yourself typing `python server.py` every morning, add this immediately. The launchd plist is ~15 lines.

**Depends on:** v1 shipped and stable.

---

## DB schema: reserve room for cross-session pattern tracking

**What:** Spend ~30 minutes designing a DB schema that doesn't block SRS (spaced repetition) in v2. Don't build SRS — just don't build a schema that makes it impossible.

**Why:** The current design is `corrections(id, ts, original, language, correction, session_id)`. To track recurring patterns across sessions, you need at minimum: a `pattern_id` FK column (nullable in v1), a `patterns` table (empty in v1), and a `session_date` column separate from `ts`. Without these, adding SRS later requires a migration and a rewrite of the insertion logic.

**Pros:** No code cost now. Migration-free v2. The recurring-patterns feature is what makes this worth keeping long-term.

**Cons:** Slightly more DB setup upfront (maybe 10 extra lines of schema).

**Context:** The biggest learning value isn't per-session corrections — it's "you wrote 'please confirm' five times this week and a native speaker would say 'can you confirm?' or 'please verify?'" You can't surface that without cross-session linkage. Design for it now.

**Depends on:** v1 prompt validation complete.
