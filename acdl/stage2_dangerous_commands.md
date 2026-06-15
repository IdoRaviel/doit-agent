# ACDL — Stage 2: Dangerous Commands

**Context:** identical structure to Stage 1 — the safety gate lives in *code*
(`src/safety.py` + the confirmation prompt in `doit`), not in the LPU context.
The only ACDL change is the content of the `INSTRUCTIONS` template, which now
asks the model to also classify the command with a `safe` flag.

## ACDL (render-ready)

```
SingleCommand[@T]: {
    S: INSTRUCTIONS
    U: env.user_request[@T]
}
```

Diagram: `diagrams/stage2.png` (same structure as Stage 1; include it for
completeness, or note "unchanged from Stage 1" in the report).

## Prompt template (`INSTRUCTIONS`) — delta from Stage 1

The `command` schema gains a `safe` field and safety rules (`src/llm.py`):

```
1. "command" — the request can be fulfilled with a shell command.
   {"type": "command", "command": "<bash command>", "explanation": "<one-line description>", "safe": <true|false>}
   Set "safe" to false if the command modifies the system: creates, moves,
   deletes, or overwrites files; changes permissions/ownership; formats disks;
   or rewrites git state. Set "safe" to true for read-only commands that only
   display information (ls, cat, grep, find, ps, df, etc.).
```

The safety decision (auto-run vs. confirm) is made by the program, not the
context: a command auto-runs only if `safe == true` AND the local regex
backstop in `src/safety.py` finds no destructive pattern.
