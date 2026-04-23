# English Coach for Claude Code

Turn your Claude Code sessions into English learning material — automatically.

Every message you type in Claude Code gets captured when the session ends, run through Claude (Haiku), and shown in a local dashboard as a before/after correction. Japanese messages become natural technical English. English messages get polished if they need it. Zero extra effort: just use Claude Code the way you normally would.

## How it works

```
Claude Code session ends
  └─> Stop hook fires
        └─> Reads your messages from the session transcript
              ├─> Detects language (Japanese or English)
              ├─> Calls Claude API for correction + explanation
              └─> Posts to local FastAPI server (127.0.0.1:8765)

Dashboard (http://127.0.0.1:8765)
  └─> Polls every 2s → shows corrections as they arrive
```

The hook is non-blocking. If the server is down or the API key is missing, Claude Code continues normally — the hook just logs and exits cleanly.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Anthropic API key ([get one here](https://console.anthropic.com/))

## Installation

```bash
git clone <your-repo-url>
cd english-coach-claude-code
uv sync
```

## Configuration

Copy the example env file and add your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

**1. Start the server**

```bash
uv run python server.py
```

The server listens on `http://127.0.0.1:8765`. It creates the SQLite database on first run.

**2. Open the dashboard**

Navigate to [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser.

**3. Use Claude Code normally**

The Stop hook in `.claude/settings.json` fires automatically when each Claude Code session ends. Your messages are extracted, corrected, and sent to the dashboard. Within ~3 seconds, you'll see the correction cards appear.

## Dashboard

The dashboard shows:
- **Latest correction** — the most recent message, highlighted at the top
- **Session history** — all corrections, with language badge, original text, corrected text, and explanation (expandable)
- **Filter by** — Today / This session / All

## Project structure

```
english_coach/
  config.py          # Central config (DB path, server host/port, model name)
  db.py              # SQLite layer (WAL mode, corrections + summaries + hook_state tables)
  jsonl_reader.py    # Reads Claude Code session transcripts, skips commands/meta
  language.py        # Unicode-based Japanese/English detection
  corrector.py       # Claude API calls (correction + explanation)
  hook.py            # Stop hook entry point
server.py            # FastAPI server
static/index.html    # Dashboard (vanilla HTML/JS, no build step)
tests/               # Pytest tests for each module
data/history.db      # SQLite database (auto-created, gitignored)
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard (index.html) |
| POST | `/api/feedback` | Insert a correction (called by the hook) |
| GET | `/api/latest?limit=20` | Most recent N corrections |
| GET | `/api/history?session_id=&limit=50&offset=0` | Paginated history |
| POST | `/api/summary` | Insert a session summary (reserved for v2) |

## Development

Run the test suite:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

The test suite covers the DB layer, JSONL reader, language detector, corrector, hook, and server. All tests are offline except `test_corrector.py`, which requires `ANTHROPIC_API_KEY` to be set.

## License

MIT
