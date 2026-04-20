from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
MODEL = "claude-haiku-4-5-20251001"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
