# Stage 4 — Clarifications: experiment outputs

Captured runs from the clarifications experiments.

---

## Answered clarification (gemini/gemini-2.5-flash)

Request is genuinely ambiguous ("by date" → which date?), so the model asks
instead of acting. User answered with the option number `2`; the model re-queried
with the answer and produced the access-date command.

```
$ doit "sort the files here by date"
Which date do you want to sort by?
1. modification date
2. access date
3. creation date
Your answer: 2
# List files in the current directory, sorted by access date (most recently accessed first).
ls -tlu

total 2672
-rwxrwxr-x 1 ido-raviel ido-raviel    5663 Jun 15 19:36 doit
drwxrwxr-x 3 ido-raviel ido-raviel    4096 Jun 15 19:35 src
...
```

## No answer → clean exit, no guessing (gemini/gemini-2.5-flash)

Same request; user did not answer (stdin closed / timeout). `doit` exits without
guessing and records an unanswered clarify turn.

```
$ doit "sort the files here by date" < /dev/null
Which date do you want to sort by?
1. modification date
2. access date
3. creation date
Your answer:
No answer within 2 minute(s) — exiting. Re-run doit when you're ready.
(exit code 0)
```

History record written:
```json
{"ts": "...", "model": "gemini/gemini-2.5-flash", "request": "sort the files here by date",
 "type": "clarify", "question": "Which date do you want to sort by?",
 "options": ["modification date", "access date", "creation date"], "answered": false}
```

## All three models — same prompt: "sort the files here by date"

Triggering a clarification is strongly model-dependent. Only the hosted model
asked; both local models skipped the fork and chose a default.

- **gemini-2.5-flash (hosted)**: ASKED — offered 3 date options (modification /
  access / creation), waited, and on answer `2` produced `ls -tlu` (access date).
  This is the assignment's intended behavior.
- **mistral:7b (local, tool-calling)**: did NOT ask — defaulted to modification
  date and ran `ls -lt`. A reasonable default, but it skipped the genuine fork.
- **llama3:8b (local, no tool-calling)**: did NOT ask AND the default was broken —
  produced `ls -1t * | sort`. `ls -1t` sorts by modification time, but piping to
  `sort` then re-sorts the names alphabetically, destroying the time ordering;
  the `*` glob also recurses into subdirectories (listing their contents). So it
  both under-asked and generated a logically incorrect command.

```
gemini   -> clarify {modification, access, creation} -> ls -tlu     (asked, correct)
mistral  -> ls -lt                                                  (defaulted, ok)
llama3   -> ls -1t * | sort                                         (defaulted, broken)
```

**Takeaway:** the "ask only when needed" judgment lives entirely in the model.
The hosted model recognized the ambiguity and asked; the local models did not.
The pattern matches Stage 3 — the non-tool model (llama3) again produced a
logically flawed command — and shows clarification quality tracks model strength,
not just the prompt.
