# ACDL — Multi-turn

**Context:** the turn is no longer stateless. Before the current request we replay
the last N persisted turns (`MAX_TURNS=8`) as user/assistant pairs, so the model
can resolve references like "now sort them" or "no, latest first". On the very
first turn there is no history. The `INSTRUCTIONS` template gains a
"conversation context" note telling the model that earlier turns may appear and
may be referred to.

## ACDL (render-ready)

```
MultiTurn[@T]: {
    S: INSTRUCTIONS
    ForEach(t: range(1, @T-1)) {
        U: env.user_request[t]
        A: resp.replay[t]
    }
    U: env.user_request[@T]
}
```

On the first turn `@T == 1`, so the history loop `range(1, @T-1)` = `range(1, 0)`
is empty and the prompt reduces to `{ S: INSTRUCTIONS, U: env.user_request[1] }`
— the stateless single-command context. The current request is always the last
message; no explicit `PromptEndsHere` marker is needed.

- `resp.replay[t]` — a rendered view of past turn `t` (in `src/history.py`,
  `_replay_assistant`): for a command turn, the command that ran plus a clipped
  output tail and exit code; for an answer/impossible turn, the text. This is the
  assistant content the model sees on replay, not the raw stored JSON.
- History is persisted in `~/.doit/history.jsonl` (append-only, one record per
  turn); only the last `MAX_TURNS` are replayed.

Diagram: `diagrams/stage3.png` (paste the block into the ACDL Live Editor,
https://acdlang26.github.io/acdlsite/visualizer.html, and export).

## Prompt template (`INSTRUCTIONS`) — delta from Stage 2

Adds a "Conversation context" block (`src/llm.py`):

```
Conversation context:
- Earlier turns of this conversation may appear before the current request,
  including commands you previously ran and their output.
- The current request may refer to a previous turn (e.g. "now sort them by date",
  "no, latest first", "why did that fail?"). When it does, resolve the reference
  using the earlier turns and respond accordingly.
```
