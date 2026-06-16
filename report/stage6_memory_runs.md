# Stage 6 — Memory: experiment outputs

Memory = durable facts/preferences persisted in `~/.doit/memory.jsonl`, separate
from per-turn history. A dedicated extraction call decides what to save; stored
memories are injected into the system prompt on every turn. "New terminal" is
simulated by clearing history (`~/.doit/history.jsonl`) while KEEPING memory.

---

## Core: store + recall across "terminals" + no duplicate

Sequence: T1 state a fact → T2 (new terminal) recall. Expect 1 memory, recall works.

### ollama/mistral:7b
```
T1  $ doit "the folder ~/school/llms/ass3 is my LLM class project folder"
    🧠 Remembered: The user's LLM class project folder is ~/school/llms/ass3.
    Your LLM class project folder is `~/school/llms/ass3`. ...
T2  $ doit "what is the path to my llm class project?"   (history cleared, memory kept)
    The path to your LLM class project is ~/school/llms/ass3
    >>> memory count: 1  (recall did NOT re-save)
```

### ollama/llama3:8b
```
T1  🧠 Remembered: The user's LLM class project folder is ~/school/llms/ass3.
T2  Your LLM class project folder is located at `~/school/llms/ass3`. ...
    >>> memory count: 1
```

### gemini/gemini-2.5-flash (partial — limited by free-tier quota)
STORE verified:
```
T1  $ doit "the folder ~/school/llms/ass3 is my LLM class project folder"
    🧠 Remembered: The user's LLM class project folder is ~/school/llms/ass3.
    Okay, I'll remember that `~/school/llms/ass3` is your LLM class project folder.
    >>> memory count: 1
```
The RECALL turn (T2) could not be captured: gemini's free tier repeatedly returned
HTTP 503 ("high demand") and 429 (rate limit) — even after a 70s wait — so the
second turn's calls were refused. This is an infrastructure limit, not a logic
issue: recall is model-agnostic and verified on both local models above.

Finding worth noting: the two-call memory design (main + extractor) makes EVERY
turn cost two requests, so hosted free-tier rate limits bite roughly twice as
fast. Local models have no such limit — a real trade-off of the always-run
extractor on metered hosted models.

---

## Case A — one request that both ACTS and stores a memory

What this tests: the assignment notes a single request may need to *do something*
AND *record a memory* at once. Test request (folder pre-created with two files so
the listing has visible output):

```
doit "list all the files in ~/school/llms/ass3, this is my llm class project folder"
```
Expected: the agent RUNS `ls ~/school/llms/ass3` (the action) AND saves the fact
"this folder is the user's LLM class project" (the memory).

Neither local model did BOTH halves — each got one and missed the other:

```
mistral:7b
  🧠 Remembered: The user's LLM class project folder is ~/school/llms/ass3.   <- memory SAVED
  You can list all the files ... with `ls ~/school/llms/ass3`.                <- only SUGGESTED, did not run
  => memory YES, action NO

llama3:8b
  # List files in the specified directory
  ls ~/school/llms/ass3
  hw1.py
  notes.md                                                                    <- action RAN
  (memory.jsonl empty)                                                        <- nothing saved
  => action YES, memory NO
```

So the combined action+memory request is the HARDEST case. Mistral saved the fact
but treated the listing as a suggestion (the trailing "this is my project folder"
clause seems to nudge it into answer-mode). Llama3 ran the listing but its
extractor judged the embedded fact not worth saving. The stronger hosted model
(gemini) is the one we'd expect to do both, but it was quota-blocked this session.

This is a consequence of the two-call design: the action and the memory decision
are SEPARATE model calls, so one can succeed while the other doesn't. Verified by
calling the extractor directly on the same input — llama3 returns
`{"save": false, "text": ""}` reproducibly (a real decision, not a parse error).
Note llama3 *did* save the same fact when stated plainly ("the folder X is my
project folder"), so it is weaker at spotting a durable fact buried inside an
action request.

A separate bug an earlier version of this case exposed (now fixed): a model
answered with an invented shape `{"type": "memory", ...}` — "memory" is not one of
our four allowed types — and the code printed the raw object. Fixes: (1) the
prompt now says type MUST be one of the four; (2) the code prints any text it
finds instead of the raw object if a model still invents a type.

---

## Case B — behavioural preference (mistral) — LIMITATION

Goal: store "ask me each time which date to sort by", then have a later sort honour it.

```
$ doit "always ask me which date to use before sorting files by date"
Which file modification date should I sort by? (creation, access, or modification)
1. creation
2. access
   -> mistral read this as a sort-NOW request and clarified; the PREFERENCE was
      not stored.
$ doit "sort the files here by date"     (later)
🧠 Remembered: The user prefers to sort files locally by modification date.  (a wrong paraphrase)
You can sort them by date with `ls -t`.   (did NOT ask, as the preference wanted)
```

So **factual recall works well, but behavioural preferences are shaky on mistral**:
it misread the preference-setting request, failed to store it, and later neither
honoured nor correctly captured it. Consistent with the recurring theme — the
weaker model handles concrete facts but struggles with subtler intent.

---

## How the design works (and why)

**Who decides what to save?** A second, separate model call — the "extractor" —
runs every turn. Its only job: look at what the user said and decide "is there a
durable fact here? if so, write it in one concise line." We use a dedicated call
(instead of asking the main model to also flag memories in its normal reply)
because the weaker local models couldn't reliably do both jobs in one response —
they kept dropping the extra field or misusing it.

**How are duplicates avoided?** Before deciding, the extractor is shown the
memories already stored ("Already known: ..."). If the new fact is already there,
it answers "don't save." This is what stopped the agent from re-saving the same
fact every time the user merely *asked about* it.

**How does the agent recall a memory later?** On every turn, all stored memories
are pasted into the system prompt. So even in a brand-new terminal, the model
sees "the user's project folder is ~/school/llms/ass3" and can answer questions
about it.

**Costs / limitations:**
- Every turn now makes **2 model calls** (the normal one + the extractor). On
  local models that's a few extra seconds.
- All memories are injected into both prompts every turn, so the prompt grows as
  memories pile up. Fine for now; a retrieval/summarization layer (a candidate
  *extension*) would keep only the relevant ones.
- `cd` runs in a subprocess, so "move to my project folder" can't actually change
  the user's shell directory (a separate problem handled in the user-awareness /
  multi-tasking stages). Recalling the path still works.
