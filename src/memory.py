"""Persistent user memories.

Unlike multi-turn history (the running conversation), memories are durable
facts/preferences about the user that persist across new terminals, directories,
and sessions. They live in a single global file and are injected into every model
call so the agent can act on them later.

A dedicated extraction call (see src/llm.py extract_memory + doit) runs every
turn and decides save/skip + condenses the text. It is given the already-stored
memories so it can avoid duplicates, so storage here is a plain append.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = Path.home() / ".doit"
MEMORY_FILE = MEMORY_DIR / "memory.jsonl"


def add_memory(text: str) -> None:
    """Append one memory (a concise fact/preference) to the global memory file."""
    text = (text or "").strip()
    if not text:
        return
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), "text": text}
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_memories() -> list[dict]:
    """Return all stored memories, oldest first."""
    if not MEMORY_FILE.exists():
        return []
    records = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def format_memories(memories: list[dict]) -> str:
    """Render memories as a system-prompt block, or '' if there are none.

    Listed oldest -> newest so the model can treat later entries as overriding
    earlier ones when they conflict.
    """
    lines = [f"- {m.get('text', '')}" for m in memories if m.get("text")]
    if not lines:
        return ""
    return (
        "Known memories about the user (durable facts/preferences; if two "
        "conflict, the LATER one wins):\n" + "\n".join(lines)
    )
