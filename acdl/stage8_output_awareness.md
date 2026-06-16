# ACDL — Stage 8: Output awareness

**No scheme change.** Output awareness ("why did that fail?", "which of these is
safe to delete?") needs no new context: the previous command's output already
lives in `resp.replay[@t]`, which `src/history.py` renders as
`Ran: <cmd>` + a clipped stdout/stderr tail + the exit code. The model reasons
over it directly. See the Stage 7 scheme (`acdl/stage7_user_awareness.md`) — it is
unchanged.

## Prompt delta from Stage 7 (`src/llm.py`)

Two lines, to ground failure explanations in real output and to not invent a
failure for a not-run command:

```
- To explain a failure, use the earlier turn's actual output / error text and
  exit code — do not invent a reason.
- A command shown as "Proposed (not run)" was NOT executed (the user declined it).
  Do not claim such a command failed; say it was not run.
```
