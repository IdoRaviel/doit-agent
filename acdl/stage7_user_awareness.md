# ACDL — Stage 7: User awareness

**Context:** the agent becomes aware of the USER's actions and location, via two
additions to the context plus a tool loop:

1. **Always injected (push):** the current working directory (`sys.cwd`) and the
   available tool list (`sys.tools`) are added to the system prompt. CWD is free —
   `doit` runs as a process launched from the user's shell, so `os.getcwd()` is
   the user's directory.
2. **On demand (pull):** the model can call a tool (`type: "tool"`) — currently
   `shell_history`, which returns the user's recent interactive commands. We run
   the tool and feed the result back, then the model continues. This is
   roll-your-own tool-use (no native tool-calling), so it works on all models.

User vs. `doit` actions separate naturally: `doit` runs commands via subprocess,
which never touch the interactive bash history, so `shell_history` returns only
the user's manual commands (and `doit ...` invocations are filtered out).

## ACDL (render-ready)

```
UserAware[@T]: {
    S: {
        INSTRUCTIONS
        AVAILABLE_TOOLS
        sys.cwd[@T]
        sys.memories
    }
    History {
        ForEach(@t: range(1, @T-1)) {
            U: env.user_request[@t]
            A: resp.replay[@t]
        }
    }
    U: env.user_request[@T]
    If resp.type[@T] == tool {
        A: resp.tool_call[@T]
        U: sys.tool_result[@T]
    }
    If resp.type[@T] == clarify {
        A: resp.clarify[@T]
        U: env.clarify_answer[@T]
    }
}
```

- `S: { ... }` — the braced multi-line role form groups everything in the system
  message: the `INSTRUCTIONS` template, the `AVAILABLE_TOOLS` template (the tool
  list rendered from the registry in `src/tools.py`), and two injected variables.
- `sys.cwd[@T]` — the current working directory, injected every turn.
- `sys.memories` — durable user memories injected into the system prompt.
- `History { ForEach(@t: range(1, @T-1)) { ... } }` — the named history block;
  `@t` is the loop variable, indexing past turns.
- `resp.tool_call[@T]` — the model's tool request (name + args).
- `sys.tool_result[@T]` — the tool's output, fed back so the model can continue.
- The two `If` blocks are intra-turn loops (tool calls and clarifications),
  bounded in code (`MAX_TOOLS`, `MAX_CLARIFY`); ACDL has no `While`.

Diagram: `../report/assets/stage7-user_awareness.png`.

## Prompt template (`INSTRUCTIONS`) — delta from Stage 6

Adds a fifth response type and the (dynamically injected) tool list + CWD:

```
5. "tool" — you need information that only a tool can provide before answering.
   {"type": "tool", "tool": "<tool name>", "args": { ... }}
   You then receive the tool's result and continue. Available tools are listed
   under "Tools". Only use a tool when it genuinely helps.

Tools (request one with a "tool" response; you then receive its result):
- shell_history: Returns the user's recent interactive shell commands ...

Current working directory: <cwd>
```
