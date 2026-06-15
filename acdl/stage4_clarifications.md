# ACDL — Stage 4: Clarifications

**Context:** the model gains a fourth response type, `clarify`. When the current
request is genuinely ambiguous and the choice materially changes the command, the
model returns a question + options instead of acting. `doit` prints them, reads
the user's answer, and appends an (assistant question, user answer) pair to the
context before re-querying — all within one `doit` invocation (`@T`). The
`If resp.type[@T] == clarify` block models that conditional append. A no-answer
within `CLARIFY_TIMEOUT=120s` exits cleanly without guessing; the bounded repeat
(`MAX_CLARIFY=3`) is program logic, not part of the context scheme.

## ACDL (render-ready)

```
Clarify[@T]: {
    S: INSTRUCTIONS
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

- `resp.clarify[@T]` — the model's question + options for the current turn.
- `env.clarify_answer[@T]` — the user's reply (an option number is mapped to its
  option text before being appended).
- The `If` conditionally appends the clarification exchange when the model asked.
  ACDL has no `While`; the repeat-until-actionable behaviour (bounded by
  `MAX_CLARIFY`) lives in `doit`, not in the context description.

Diagram: `diagrams/stage4_clarifications.png` (paste the block into the ACDL Live Editor,
https://acdlang26.github.io/acdlsite/visualizer.html, and export).

## Prompt template (`INSTRUCTIONS`) — delta from Stage 3

Adds the `clarify` type and a "use sparingly" rule (`src/llm.py`):

```
4. "clarify" — the request is genuinely ambiguous AND the choice materially
   changes the command, with no clearly-best default.
   {"type": "clarify", "question": "<one short question>", "options": ["<opt 1>", "<opt 2>", ...]}

- If the request is ambiguous but a reasonable default exists, pick the most
  sensible command — do NOT ask. Use "clarify" sparingly: only when the options
  lead to materially different commands and no default is clearly right (e.g.
  "sort by date" → creation vs. access vs. modification date).
- After the user answers a clarification, produce the appropriate response
  (usually a "command") using their choice.
```
