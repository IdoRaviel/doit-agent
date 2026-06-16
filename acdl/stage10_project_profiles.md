# ACDL — Stage 10: Project profiles (extension)

**Small scheme delta from Stage 9:** one more item in the system block,
`sys.project` — the nearest `.doit.md` (searched from cwd up the tree), injected
so per-folder instructions apply. Everything else is identical to Stage 9 (the
multi-step tool/clarify loop, session-scoped History). It is a pure context
injection — no new model call, response type, or loop.

```
ProjectProfile[@T]: {
    S: {
        INSTRUCTIONS
        AVAILABLE_TOOLS
        sys.cwd[@T]
        sys.project[@T]      # nearest .doit.md, if any
        sys.memories
    }
    History { ForEach(@t: sys.session_turns[@T]) { U: env.user_request[@t]  A: resp.replay[@t] } }
    U: env.user_request[@T]
    ForEach(@k: range(1, MAX_STEPS)) {
        If resp.type[@T, @k] == tool {
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

- `sys.project[@T]` — contents of the nearest `.doit.md` (capped), rendered with a
  "follow these unless the user overrides" preamble (`src/project.py`).

Diagram: `diagrams/stage10-project_aware.png` — same shape as Stage 9 with one
extra `sys.project[@T]` line in the system block.

No `INSTRUCTIONS` change — the injected block is self-describing.
