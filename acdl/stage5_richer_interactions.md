# ACDL — Stage 5: Richer interactions

**Context:** structurally identical to Stage 4 — same scheme (system + replayed
history + current request + conditional clarify block). Richer interactions are a
*prompt-only* change: the model learns to (a) answer "how do I…" questions with a
suggestion instead of executing, and (b) act on follow-ups like "execute it" /
"modify it to …" by reading the previous turn from the replayed history. No new
context structure, so no scheme change.

## ACDL (render-ready)

```
RicherInteractions[@T]: {
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

Diagram: same structure as Stage 4 — see `../report/assets/stage4_clarifications.png`
(richer interactions add no new context scheme). Follow-up
resolution ("execute it" → run the previously suggested command) works entirely
through the existing `resp.replay[t]` history replay; it is not a new context
element.

## Prompt template (`INSTRUCTIONS`) — delta from Stage 4

The `answer` type now covers "how do I…" requests; new rules separate asking-HOW
from asking-to-DO, handle execute/modify follow-ups, and a one-shot example pins
the "modify stays a suggestion" behaviour (the rules alone were not enough for
mistral — the example fixed it). `src/llm.py`:

```
2. "answer" — ... or a "how do I..." style request for information (NOT an
   instruction to act now). For "how do I / how can I / what is the command
   for..." questions, EXPLAIN and include the suggested command inline in
   backticks, but do NOT execute it.

- Distinguish asking HOW from asking to DO: "how do I delete these?" is an
  "answer"; "delete these" is a "command".
- A previous "answer" only SUGGESTED a command and did NOT run it; an executed
  command appears in history as "Ran: <cmd>".
- "modify it to ..." → keep the same mode as before (suggestion stays an answer
  with the updated command; an executed command stays a command).
- "run it" / "execute it" / "do it" → type "command", running the most recent
  command (the one suggested or last run).

Example (note how "modify it" stays an answer):
  User: how do I delete the log files here?
  You:  {"type": "answer", "text": "You can delete them with `rm *.log`."}
  User: modify it to also remove .tmp files
  You:  {"type": "answer", "text": "Use `rm *.log *.tmp` to remove both."}
  User: execute it
  You:  {"type": "command", "command": "rm *.log *.tmp", "explanation": "...", "safe": false}
```
