# gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

Available gstack skills:
`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke context-save
- Writing or reviewing implementation code → invoke karpathy-guidelines first

## Tech stack

- Language: Python (managed by **uv**, see `pyproject.toml`)
- Server: FastAPI + uvicorn, listening on `127.0.0.1:8765`
- UI: Vanilla HTML/JS served as static files by FastAPI (`static/index.html`)
- DB: SQLite with WAL mode (`data/history.db`)
- LLM: Anthropic Claude API (`claude-haiku-4-5-20251001`)
- Hook runtime: `uv run python -m english_coach.hook` (Claude Code Stop hook)

## Key documents

- `docs/PLAN.md` — v1 implementation plan (steps, DB schema, data flow)
- `docs/designs_english_coach.md` — product design spec
- `docs/architecture_english_coach.md` — architecture spec
