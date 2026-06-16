# ACDL — Stage 6: Memory

**Context:** memory touches TWO contexts per turn.

1. **Main context** — the normal turn context, now with durable memories injected
   into the system prompt (`sys.memories`) so the model can resolve references
   ("my project folder") and adjust behaviour. This is the scheme change vs.
   Stage 5.
2. **Extraction context** — a SEPARATE, focused call (its own system prompt) that
   runs every turn and decides whether the turn holds a durable fact worth saving
   and condenses it. It is given the user's request, what the agent did, and the
   already-known memories (so it won't duplicate). Kept separate so the main model
   is not asked to do two jobs in one response.

## ACDL (render-ready)

Main context:

```
MemoryAware[@T]: {
    S: INSTRUCTIONS
    S: sys.memories
    ForEach(t: range(1, @T-1)) {
        U: env.user_request[t]
        A: resp.replay[t]
    }
    U: env.user_request[@T]
    If resp.type[@T] == clarify {
        A: resp.clarify[@T]
        U: env.clarify_answer[@T]
    }
}
```

Extraction context (separate call, same turn):

```
ExtractMemory[@T]: {
    S: MEMORY_INSTRUCTIONS
    U: env.user_request[@T]
    U: resp.action[@T]
    U: sys.memories
}
```

- `sys.memories` — durable facts/preferences from `~/.doit/memory.jsonl`. In the
  main context they are appended to the system prompt; in the extraction context
  they are shown as "Already known" so the extractor returns save:false for facts
  already stored.
- `resp.action[@T]` — a short summary of what the agent did this turn (the command
  or answer text), so the extractor has context for its decision.

Diagrams: `../report/assets/stage6-Memory.png` (shows both the main and the extraction
contexts).

## Prompt templates — delta from Stage 5

Main `INSTRUCTIONS` gains a Memory section (USE memories; saving is handled
elsewhere) and a rule that `type` must be one of the four (weak models otherwise
invent a `memory` type):

```
Memory:
- You may be given "Known memories about the user". Use them to resolve
  references and adjust behaviour. Deciding what to SAVE is handled separately —
  you only need to USE the memories you are given.

- The "type" value MUST be exactly one of: command, answer, impossible, clarify.
  Never invent other type values. If the user only states a fact for you to
  remember (no action), use "answer" to briefly confirm.
```

New `MEMORY_INSTRUCTIONS` (the extractor's system prompt) decides save/skip +
condenses, saving only NEW asserted facts and skipping anything already known.
