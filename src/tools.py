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

BASH_HISTORY = Path.home() / ".bash_history"


def _shell_history(n: int = 20) -> str:
    """Return up to `n` of the user's recent shell commands (most recent last).

    Filters out `doit ...` invocations so the result is the user's *manual* shell
    activity. Requires bash to flush history (see the PROMPT_COMMAND hook in the
    README) for in-session freshness.
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 20
    if not BASH_HISTORY.exists():
        return "(no shell history file found)"
    lines = BASH_HISTORY.read_text(encoding="utf-8", errors="replace").splitlines()
    cmds = [ln for ln in lines if ln.strip() and not ln.strip().startswith("doit ")]
    recent = cmds[-n:]
    return "\n".join(recent) if recent else "(no recent user commands)"


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
