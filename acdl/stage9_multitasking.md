# ACDL — Stage 9: Multi-tasking

**Mostly the Stage 7 scheme**, with one change and two new tools:

- **History is now session-scoped.** The `History` block replays only the current
  terminal's turns — `ForEach` iterates `sys.session_turns[@T]` (turns whose
  `session` matches this terminal) instead of all turns. So each window sees only
  its own stream by default.
- **Cross-window access is via the existing tool loop** (no new structure): two
  tools, `list_sessions` (catalog of other sessions + summaries) and
  `session_history(id)`, let the model bridge a phrase like "the other window" to
  a session and read it. These ride the same `If resp.type[@T] == tool` block from
  Stage 7.

```
MultiTask[@T]: {
    S: {
        INSTRUCTIONS
        AVAILABLE_TOOLS          # now includes list_sessions, session_history
        sys.cwd[@T]
        sys.memories
    }
    History {                    # CURRENT SESSION ONLY
        ForEach(@t: sys.session_turns[@T]) {
            U: env.user_request[@t]
            A: resp.replay[@t]
        }
    }
    U: env.user_request[@T]
    ForEach(@k: range(1, MAX_STEPS)) {        # intra-turn agent loop: step @k
        If resp.type[@T, @k] == tool {        # e.g. list_sessions THEN session_history
            A: resp.tool_call[@T, @k]
            U: sys.tool_result[@T, @k]
        }
        ElseIf resp.type[@T, @k] == clarify {
            A: resp.clarify[@T, @k]
            U: env.clarify_answer[@T, @k]
        }
    }
}
```

- The `ForEach(@k: ...)` is the intra-turn agent loop: within one `doit`
  invocation (`@T`) the model is re-called at each step `@k`. If step `@k` is a
  tool call we run it and feed the result back; if it is a clarification we ask
  the user; otherwise (command/answer/impossible) neither branch fires and the
  loop ends — that final response is the action. A cross-window request runs as
  `@k=1` → `list_sessions`, `@k=2` → `session_history(id)`, `@k=3` → the command.
- `MAX_STEPS` stands for the code bounds (`MAX_TOOLS` / `MAX_CLARIFY`).
- Session id = `$DOIT_SESSION` or the launching shell's pid (`current_session()`).
  Stale sessions are pruned lazily (`prune_stale`), not in the context.

Diagram: `diagrams/stage9-multi_task.png` — differs from Stage 7: session-scoped
`History` and the `ForEach(@k)` multi-step tool/clarify loop.

## Prompt delta from Stage 7 (`src/llm.py`)

```
- The history you see is only THIS terminal's. If the user refers to another
  terminal/window ("the other window", "window 2", "what I did over there"), call
  the list_sessions tool, match their description to a session, then call
  session_history with that id to see and reuse what was done there.
```
