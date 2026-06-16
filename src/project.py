"""Project profiles (extension).

A per-directory `.doit.md` file lets the agent behave differently in different
projects — the equivalent of an `agent.md`. When `doit` runs, it searches the
current directory and its parents for the nearest `.doit.md` and injects it into
the system prompt, so project-specific instructions (conventions, danger zones,
preferred tools) apply automatically within that folder tree.

Reuses the same context-injection pattern as cwd/memories — no extra model call.
"""

from pathlib import Path

PROFILE_NAME = ".doit.md"
PROFILE_CLIP = 2000  # cap injected profile size (chars)


def find_project_profile(start: Path | None = None) -> str:
    """Return the contents of the NEAREST .doit.md, or "" if none exists.

    "Nearest" = walk UP from `start` (default: cwd) through parent directories
    (cwd -> parent -> ... -> /) and use the FIRST .doit.md found, then stop — like
    git locating .git. So a profile applies anywhere below it, and a closer
    .doit.md in a subfolder overrides a more general one higher up (only one is
    used, never a merge). Contents are clipped to PROFILE_CLIP chars.
    """
    start = (start or Path.cwd()).resolve()
    for directory in [start, *start.parents]:
        candidate = directory / PROFILE_NAME
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace").strip()
            if len(text) > PROFILE_CLIP:
                text = text[:PROFILE_CLIP] + "\n…(profile truncated)"
            return text
    return ""


def format_profile(profile: str) -> str:
    """Render the profile as a system-prompt block, or '' if there is none."""
    if not profile:
        return ""
    return (
        "Project profile (instructions for this folder; follow them unless the "
        "user overrides):\n" + profile
    )
