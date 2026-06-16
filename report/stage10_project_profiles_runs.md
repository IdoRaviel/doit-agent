# Stage 10 — Extension: experiment outputs

## Three candidate extensions (describe three, implement one)

1. **Context compaction / summarization for long histories.**
   *What:* today we replay only the last `MAX_TURNS=8` turns of a session, so
   older context is simply dropped. Compaction would instead summarize the turns
   that fall out of the window into a short running "summary so far" note that is
   injected alongside the recent turns, so early context (decisions, paths, the
   task goal) survives in long sessions.
   *How it would be implemented:* when a session's turn count crosses a threshold,
   make a dedicated summarization model call over the oldest turns, store the
   result (e.g. a `summary` record per session in `~/.doit/`), and prepend it to
   the replayed history; refresh it as more turns age out.
   *Why harder:* it needs an extra model call (cost/latency, and a quality risk —
   a bad summary silently corrupts later context), plus invalidation logic
   (when to re-summarize, how to avoid summarizing the summary repeatedly).
   *Capability:* context management.

2. **Project profiles (`.doit.md`)** — per-directory instructions so the agent
   behaves differently in different folders (the `agent.md` idea). Capability:
   remembering / per-project context. *Implemented (below).*

3. **Command plans** — one request → a proposed numbered sequence of shell
   commands, shown up front, then executed step-by-step.
   *What:* for a multi-command task ("set up a Python project"), the agent first
   presents a plan (`1. mkdir src  2. python -m venv .venv  3. pip install -r
   requirements.txt`), the user approves, then each step runs in order — each
   destructive step still passing the safety gate, and the plan adapting if a step
   fails.
   *How it would be implemented:* a new `plan` response type carrying a list of
   steps; an execution loop over the steps (reusing the safety confirmation and
   the output feedback); on a failed step, feed the error back and let the model
   revise the remaining plan.
   *Why harder:* a new response type + a multi-command execution loop with
   per-step confirmation and failure handling/replanning — the most code of the
   three, and the most ways to go wrong mid-sequence.
   *Capability:* planning / multi-step execution.

Note: multi-step *tool* use already exists in the core (the `ForEach(@k)` agentic
loop chains tool/clarify steps, e.g. cross-window `list_sessions` →
`session_history`), so it is not used as the "additional" extension.

## Why project profiles

Easiest to implement cleanly and clearly additional: it reuses the existing
context-injection pattern (like cwd/memories) with NO new model call, response
type, or loop — yet it is a genuine agent capability (per-project behaviour).

## How it works
`src/project.py` finds the **nearest** `.doit.md`: starting from the current
directory it walks UP through parent directories (cwd → parent → … → `/`) and
uses the FIRST `.doit.md` it finds — stopping there (like how `git` locates its
`.git`). Consequences:
- a profile in `~/code/myapp/` applies anywhere under `myapp/` (walk-up from
  subdirectories);
- if two exist, the closer one wins (a subfolder `.doit.md` overrides a general
  one higher up) — only one profile is used, not a merge;
- if none exists up to `/`, nothing is injected (zero cost outside projects).

It caps the contents and `doit` injects them into the system prompt as a
"Project profile" block.

## Demo
Project `.doit.md`:
```
This is a demo project.
- When listing files, ALWAYS use long format with human-readable sizes (ls -lh).
- Never modify or delete anything under ./sacred/.
```
```
$ cd /tmp/projtest && doit "list the files here"
# List files ... with long format and human-readable sizes
ls -lh                       # <- default would be plain `ls`; the profile changed it
$ cd /tmp/projtest/sub && doit "list the files here"
ls -lh                       # <- walk-up found the profile from a subdirectory
```

Both local models honoured it (mistral and llama3 both produced `ls -lh`). Because
the profile is PUSHED into context (not a tool the model must decide to call),
even the non-tool model applies it reliably — same pattern as output-awareness.
