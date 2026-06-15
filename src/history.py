"""Persistent multi-turn history.

Each `doit` invocation is a separate process, so to support follow-ups like
"now sort them by date" we persist every turn to an append-only JSONL file in
~/.doit/ and replay the last N turns into the model's message list.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_DIR = Path.home() / ".doit"
HISTORY_FILE = HISTORY_DIR / "history.jsonl"

# How many recent turns to replay into the model context, and how much of each
# command's output to keep (chars). Bounded so context stays small and the model
# doesn't drift on stale turns.
MAX_TURNS = 8
OUTPUT_CLIP = 1000


def append_turn(record: dict) -> None:
    """Append one turn record to the history file (creating ~/.doit/ if needed)."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), **record}
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_recent(limit: int = MAX_TURNS) -> list[dict]:
    """Return up to `limit` most-recent turn records, oldest first."""
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _clip(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= OUTPUT_CLIP:
        return text
    return text[:OUTPUT_CLIP] + "\n…(output truncated)"


def _replay_assistant(turn: dict) -> str:
    """Render a past turn as the assistant content the model sees on replay."""
    ttype = turn.get("type")
    if ttype == "command":
        cmd = turn.get("command", "")
        if not turn.get("executed", False):
            return f"Proposed (not run): {cmd}"
        parts = [f"Ran: {cmd}"]
        out = _clip(turn.get("stdout", ""))
        err = _clip(turn.get("stderr", ""))
        if out:
            parts.append(f"Output:\n{out}")
        if err:
            parts.append(f"Errors:\n{err}")
        parts.append(f"(exit code {turn.get('returncode', 0)})")
        return "\n".join(parts)
    if ttype == "impossible":
        return f"Not possible: {turn.get('text', '')}"
    return turn.get("text", "")


def build_messages(system_prompt: str, history: list[dict], user_request: str) -> list[dict]:
    """Assemble the full message list: system + replayed history + current request."""
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": "user", "content": turn.get("request", "")})
        messages.append({"role": "assistant", "content": _replay_assistant(turn)})
    messages.append({"role": "user", "content": user_request})
    return messages
