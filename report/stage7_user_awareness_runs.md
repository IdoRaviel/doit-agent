# Stage 7 — User awareness: experiment outputs

The agent learns about the USER (not just its own actions) two ways:
- **CWD** injected into the system prompt every turn (free: `doit` inherits the
  shell's directory).
- **shell_history** as a TOOL the model calls (roll-your-own tool-use): it returns
  the user's recent interactive commands. `doit`'s own commands run via subprocess
  and never enter bash history, so user vs. doit actions separate naturally; the
  tool also filters out `doit ...` invocation lines.

For these runs `~/.bash_history` was seeded with known commands. (In real use a
`PROMPT_COMMAND='history -a'` hook keeps it fresh — see README.)

---

## Tool use: "summarize what I just did" (mistral)

Seeded history: `cd ~/school/llms/ass3`, `mkdir data`, `python train.py`,
`ls -la`, and a `doit "list the files"` line (must be filtered).

```
$ doit "summarize what I just did in the shell"
You recently navigated to your school project directory, created a new folder
named 'data', ran a Python script called 'train.py', and then listed the
contents of the current directory in long format.
```
Correct, and it omitted the `doit "list the files"` line. The summary matches the
seeded commands exactly — only possible if the `shell_history` tool was actually
called and its result used.

## Proof the tool really ran (unguessable history)

Seeded: `cd /opt/zephyr-quux`, `./run_glorbax.sh --frobnicate 7`, `export WIBBLE=42`.

```
mistral:7b  ->  "You recently ran `cd /opt/zephyr-quux`, `./run_glorbax.sh
                 --frobnicate 7`, and `export WIBBLE=42`."        (tool CALLED, correct)

llama3:8b   ->  "You ran `Ran: ls -l`."                            (HALLUCINATED)
```

Verified by inspecting the raw first response: llama3 returned
`{"type": "answer", "text": "You ran `Ran: ls -l`."}` — it never emitted a tool
request at all. So the tool-trained model (mistral) correctly decides to call the
tool; the non-tool model (llama3) does not, and fabricates an answer (even echoing
the internal "Ran:" history-replay format). This is the clearest tool-use
divergence between the two local models.

## CWD awareness (mistral)

```
$ cd src && doit "which directory am I currently in?"
/home/ido-raviel/University/LLM/doit-agent/src
```
Answered the correct directory directly from the injected `Current working
directory:` line — no `pwd` needed.

---

## Notes / limitations

- Tool-use is model-dependent: mistral calls `shell_history` reliably; llama3
  fails to call it and hallucinates (consistent with earlier stages — the
  non-tool model handles structure but misses agentic decisions).
- Two memory false-positives were found and fixed here (the memory + user-awareness
  features interfering): (1) "summarize what I did" saved the activity summary as a
  durable fact; (2) a one-off "delete all .log files here" was saved as "the user
  prefers deleting .log files". The extractor prompt now excludes activity
  summaries AND one-off action requests (a preference needs lasting language like
  "always/never/each time/from now on" or an explicit "remember"). Re-tested:
  one-off `rm` saves nothing; "from now on always ask before deleting" saves
  correctly.
- Freshness depends on bash flushing history (`PROMPT_COMMAND='history -a'`);
  without it, the most recent in-session commands may be missing.
- gemini not run here (free-tier rate limits during this session); the mechanism
  is model-agnostic and the tool-call decision is what differs by model.
