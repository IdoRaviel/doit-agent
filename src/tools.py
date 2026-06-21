"""Roll-your-own tool registry.

The model can request a tool by replying with a `tool` response (structured JSON);
doit runs the tool and feeds the result back, then the model continues. This is
tool-use WITHOUT native provider tool-calling, so it works across all three model
classes. The available tools are listed to the model in the system prompt
(see `format_tools`).

First tool: `shell_history` — the user's recent interactive shell commands. This
is how the agent becomes aware of what the USER did (vs. what doit itself did:
doit runs commands via subprocess, which never touch the interactive bash
history, so the two streams separate naturally).
"""

from pathlib import Path

from src.history import list_other_sessions, session_recent

def _find_history_file() -> Path | None:
    """Return the shell history file path, checking HISTFILE then common locations."""
    import os
    histfile = os.environ.get("HISTFILE")
    if histfile:
        p = Path(histfile)
        if p.exists():
            return p
    for candidate in [Path.home() / ".zsh_history", Path.home() / ".bash_history"]:
        if candidate.exists():
            return candidate
    return None


def _shell_history(n: int = 20) -> str:
    """Return up to `n` of the user's recent shell commands (most recent last).

    Filters out `doit ...` invocations so the result is the user's *manual* shell
    activity. Supports both zsh and bash history files.
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 20
    hist = _find_history_file()
    if hist is None:
        return "(no shell history file found)"
    raw = hist.read_text(encoding="utf-8", errors="replace")
    # zsh extended history format: ": <timestamp>:<elapsed>;<command>"
    lines = []
    for ln in raw.splitlines():
        if ln.startswith(": ") and ";" in ln:
            ln = ln.split(";", 1)[1]
        lines.append(ln)
    cmds = [ln for ln in lines if ln.strip() and not ln.strip().startswith("doit ")]
    recent = cmds[-n:]
    return "\n".join(recent) if recent else "(no recent user commands)"


def _list_sessions() -> str:
    """List other terminal sessions with a short summary of each (no args)."""
    return list_other_sessions()


def _session_history(session: str = "") -> str:
    """Return another session's recent turns. args: {"session": "<id>"}."""
    if not session:
        return "(provide a session id from list_sessions)"
    return session_recent(session)


# Registry: tool name -> {description (shown to the model), func}
TOOLS = {
    "shell_history": {
        "description": (
            "Returns the user's recent interactive shell commands — what THEY "
            "typed manually (not commands doit ran). Use it for requests about "
            "what the user did or their recent actions. args: {\"n\": <count, "
            "default 20>}"
        ),
        "func": _shell_history,
    },
    "list_sessions": {
        "description": (
            "Lists OTHER terminal sessions (windows), each with a summary of what "
            "was done there. Use it when the user refers to another window/session "
            "(e.g. 'the other window', 'window 2'); match their description to a "
            "session, then call session_history with its id. No args."
        ),
        "func": _list_sessions,
    },
    "session_history": {
        "description": (
            "Returns the recent turns of another session so you can reuse what was "
            "done there. args: {\"session\": \"<id from list_sessions>\"}"
        ),
        "func": _session_history,
    },
}


def format_tools() -> str:
    """Render the available tools as a system-prompt block."""
    lines = ["Tools (request one with a \"tool\" response; you then receive its result):"]
    for name, spec in TOOLS.items():
        lines.append(f"- {name}: {spec['description']}")
    return "\n".join(lines)


def run_tool(name: str, args: dict | None) -> str:
    """Execute a registered tool by name; never raises (returns an error string)."""
    spec = TOOLS.get(name)
    if not spec:
        return f"(unknown tool: {name})"
    args = args or {}
    try:
        return spec["func"](**args)
    except TypeError:
        try:
            return spec["func"]()
        except Exception as e:  # noqa: BLE001
            return f"(tool error: {e})"
    except Exception as e:  # noqa: BLE001
        return f"(tool error: {e})"
