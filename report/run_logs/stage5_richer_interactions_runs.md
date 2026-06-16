# Stage 5 — Richer interactions: experiment outputs

Sequence (one "how do I" thread with follow-ups):

1. `doit "how do I list the 3 largest files in this directory?"`  → expect ANSWER
2. `doit "modify it to show the 5 largest"`                        → expect ANSWER (updated suggestion)
3. `doit "execute it"`                                             → expect COMMAND (runs)

---

## gemini/gemini-2.5-flash (hosted)

Followed the design first try (rules only, before the example was added):

```
T1 (answer)  You can list the 3 largest files ... 
             `find . -maxdepth 1 -type f -print0 | xargs -0 du -h | sort -rh | head -n 3`
T2 (answer)  ...changing head -n 3 to head -n 5:
             `find . -maxdepth 1 -type f -print0 | xargs -0 du -h | sort -rh | head -n 5`
T3 (command) find . -maxdepth 1 -type f -print0 | xargs -0 du -h | sort -rh | head -n 5
             -> ran, listed the 5 largest
```
History types: `answer`, `answer`, `command`.

## ollama/mistral:7b (local, tool-calling) — needed the example

**Before** the one-shot example (rules only): T2 "modify it" was wrongly turned
into a `command` (and even flagged read-only `ls -lS | head` as dangerous):

```
T1 (answer)  ... `ls -lS | head -n 3`
T2 (command) ls -lS | head -n 5      <-- WRONG: should stay a suggestion
```

**After** adding a one-shot example to the prompt: correct.

```
T1 (answer)  You can list the 3 largest files in this directory with `ls -lS | head -n3`.
T2 (answer)  Use `ls -lS | head -n5` to show the 5 largest files
T3 (command) ls -lS | head -n5   -> ran, listed the 5 largest
```
History types: `answer`, `answer`, `command`.

## ollama/llama3:8b (local, no tool-calling) — flow right, command wrong

Got the answer/modify/execute FLOW correct (all types right, no example needed),
but the command quality was poor again:

```
T1 (answer)  You can use `du -a | sort -n -r | head -n 3` to list the 3 largest files.
T2 (answer)  Use `du -a | sort -n -r | head -n 5` to list the 5 largest files.
T3 (command) du -a | sort -n -r | head -n 5
             -> listed DIRECTORIES recursively (., ./.venv, ./.venv/lib, ...),
                not the top-level files asked for
```
History types: `answer`, `answer`, `command`.

`du -a` recurses into every subdirectory (including `.venv`, thousands of files)
and reports directory sizes; the result is not "the largest files in this
directory". Contrast gemini's correct `find . -maxdepth 1 -type f ... | sort -rh`.

---

## Notes / model difference

- The capability is **prompt-only** (no code change beyond the prompt): "how do I"
  → answer; "execute it"/"modify it" resolved from the replayed history.
- **gemini** honoured the "modify stays a suggestion" rule from the rules alone,
  and produced a correct command (`find -maxdepth 1 -type f`).
- **mistral** got the flow right only AFTER a one-shot example was added — a
  weaker instruction model needs examples, not just rules. Command was fine.
- **llama3** got the flow right WITHOUT the example (types all correct), but the
  command was wrong (`du -a` recurses and lists directories, not top-level files).
  So across the three: gemini = flow + command correct; mistral = flow needs an
  example, command ok; llama3 = flow ok, command logic poor. Consistent with
  Stages 3–4: the non-tool model handles structure but fumbles shell logic.
- mistral also (before the fix) over-flagged a read-only pipe (`ls -lS | head`) as
  unsafe via its own `safe:false` — caught by the confirmation gate, harmless, but
  shows its safety judgement is noisier than gemini's.
- Bug fixed during this stage: the dangerous-command `Proceed?` prompt used bare
  `input()`, which crashed with EOFError on closed stdin; now caught and treated
  as "no" (abort).
