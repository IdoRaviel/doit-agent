"""Persistent multi-turn history.

Each `doit` invocation is a separate process, so to support follow-ups like
"now sort them by date" we persist every turn to an append-only JSONL file in
~/.doit/ and replay the last N turns into the model's message list.

Multi-tasking: every record is tagged with a `session` id (one per terminal), so
each terminal sees only its own history by default. Cross-window references
("do the same thing I did in the other window") are served by the session tools
in src/tools.py, which read other sessions via the helpers here. Stale sessions
are pruned lazily.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

HISTORY_DIR = Path.home() / ".doit"
HISTORY_FILE = HISTORY_DIR / "history.jsonl"

# How many recent turns to replay into the model context, and how much of each
# command's output to keep (chars). Bounded so context stays small and the model
# doesn't drift on stale turns.
MAX_TURNS = 8
OUTPUT_CLIP = 1000
STALE_DAYS = 7  # sessions untouched for this long are pruned lazily


def current_session() -> str:
    """Stable id for the terminal that launched doit.

    Prefers $DOIT_SESSION (set by an optional .bashrc snippet); otherwise falls
    back to the parent process id — the launching shell, which is constant across
    invocations within one terminal and differs between terminals. So multi-tasking
    works out of the box, with the env var as an explicit override.
    """
    return os.environ.get("DOIT_SESSION") or str(os.getppid())


def append_turn(record: dict) -> None:
    """Append one turn record (tagged with timestamp + session) to the history."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session": current_session(),
        **record,
    }
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_all() -> list[dict]:
    """Return every stored turn record, oldest first."""
    if not HISTORY_FILE.exists():
        return []
    records = []
    for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def load_recent(limit: int = MAX_TURNS) -> list[dict]:
    """Return up to `limit` most-recent turns FROM THE CURRENT SESSION, oldest first."""
    session = current_session()
    mine = [r for r in load_all() if r.get("session") == session]
    return mine[-limit:]


def prune_stale(days: int = STALE_DAYS) -> None:
    """Drop turns belonging to sessions whose latest activity is older than `days`.

    Lazy garbage collection of closed terminals — robust to crashes/kills (no
    reliance on a shell close hook). The current session is always kept.
    """
    if not HISTORY_FILE.exists():
        return
    records = load_all()
    if not records:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    keep_now = current_session()

    # Latest activity per session.
    last_seen: dict[str, datetime] = {}
    for r in records:
        sid = r.get("session", "")
        try:
            ts = datetime.fromisoformat(r.get("ts", ""))
        except ValueError:
            continue
        if sid not in last_seen or ts > last_seen[sid]:
            last_seen[sid] = ts

    fresh = {s for s, ts in last_seen.items() if ts >= cutoff or s == keep_now}
    if fresh == set(last_seen):
        return  # nothing to prune
    kept = [r for r in records if r.get("session") in fresh]
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


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


# --- Cross-session access (used by the session tools in src/tools.py) ----------

def list_other_sessions(max_requests: int = 3) -> str:
    """A human-readable catalog of OTHER sessions, so the model can match a phrase
    like "the other window" to a session id, then fetch it with session_history."""
    here = current_session()
    by_session: dict[str, list[dict]] = {}
    for r in load_all():
        by_session.setdefault(r.get("session", ""), []).append(r)

    lines = []
    for sid, recs in by_session.items():
        if sid == here or not sid:
            continue
        last_active = recs[-1].get("ts", "?")
        requests = [r.get("request", "") for r in recs if r.get("request")]
        recent = "; ".join(requests[-max_requests:]) or "(no requests)"
        lines.append(f"- session {sid} (last active {last_active}): {recent}")
    if not lines:
        return "(no other sessions)"
    return "Other terminal sessions:\n" + "\n".join(lines)


def session_recent(session_id: str, limit: int = MAX_TURNS) -> str:
    """Render the recent turns of another session (for the session_history tool)."""
    recs = [r for r in load_all() if r.get("session") == str(session_id)]
    if not recs:
        return f"(no history for session {session_id})"
    lines = []
    for turn in recs[-limit:]:
        lines.append(f"user: {turn.get('request', '')}")
        lines.append(_replay_assistant(turn))
    return "\n".join(lines)
