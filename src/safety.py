import re

# Local "defense in depth" backstop. Even if the LLM marks a command safe,
# any match here forces a confirmation prompt. Patterns target commands that
# create, move, delete, or overwrite filesystem state.
DANGER_PATTERNS = [
    (r"\brm\b", "deletes files/directories"),
    (r"\brmdir\b", "removes directories"),
    (r"\bmv\b", "moves/renames files"),
    (r"\bdd\b", "low-level disk write"),
    (r"\bmkfs\b", "formats a filesystem"),
    (r"\bchmod\b", "changes permissions"),
    (r"\bchown\b", "changes ownership"),
    (r"\btruncate\b", "shrinks/empties files"),
    (r"\bshred\b", "securely erases files"),
    (r">>?", "redirects output into a file (can overwrite)"),
    (r"\bmkdir\b", "creates directories"),
    (r"\btouch\b", "creates/updates files"),
    (r"\bln\b", "creates links"),
    (r"\bgit\s+(reset|clean|checkout|rebase)\b", "rewrites git state"),
    # `find ... -delete` / `find ... -exec <cmd>` don't contain rm/mv literally
    (r"-delete\b", "deletes matched files (find -delete)"),
    (r"\bfind\b.*-exec\b", "runs a command on matched files (find -exec)"),
]


def local_danger_check(command: str) -> tuple[bool, str]:
    """Return (is_dangerous, reason). Reason is empty when safe."""
    for pattern, reason in DANGER_PATTERNS:
        if re.search(pattern, command):
            return True, reason
    return False, ""
