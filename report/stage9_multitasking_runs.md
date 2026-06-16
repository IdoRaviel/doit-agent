# Stage 9 — Multi-tasking: experiment outputs

Each terminal gets a `session` id (`$DOIT_SESSION`, else the launching shell's
pid). History is tagged with it; `load_recent()` returns only the current
session's turns. Cross-window references use two tools (`list_sessions`,
`session_history`). Stale sessions are pruned lazily. Tests simulate two windows
via `DOIT_SESSION=win1 / win2`.

## Session isolation (the assignment's example)
```
W1  $ doit "list the files in this directory"          -> ls (+ listing)
W2  $ doit "create a folder for each year 2020..2026"  -> for i in {2020..2026}; do mkdir -p ./years/$i; done
W1  $ doit "sort them by size"                         -> ls -lS
```
W1's "sort them" sorted the FILE LISTING from W1 — it did NOT touch W2's year
folders. Recorded sessions: `win1 | list...`, `win2 | create folders...`,
`win1 | sort...`. So each window's "them" stays within its own stream.

## Cross-window reference (memory cleared, so tools are the only path)
```
W1  $ doit "now do the same folder task we did in the other window, here"
    for i in {2020..2026}; do mkdir -p ./years/$i; done
```
W1 reproduced W2's EXACT command (note the distinctive `./years/` nesting). Since
W1's own history has no folder task and memory was cleared, the model could only
get this by calling `list_sessions` (to find W2 by its summary) then
`session_history(win2)`. Both models reproduced it:
- mistral:7b — correct.
- llama3:8b — also correct here (reproduced the exact `./years/` command, implying
  it used the tools). BUT llama3's tool-use is INCONSISTENT — in Stage 7 it failed
  to call `shell_history` at all. So weak-model cross-window behaviour is not
  reliable; the strong path is the tool-trained model.

## Notes / limitations
- Session id defaults to the launching shell's pid (os.getppid()), so isolation
  works with NO setup; `$DOIT_SESSION` (a one-line .bashrc snippet) is an explicit
  override (see README).
- Pruning is lazy/staleness-based (sessions idle > 7 days), not tied to terminal
  close (close events are unreliable — kill/crash/SSH-drop don't fire a hook).
- Memory false-positive recurred: W2's one-off "create folders" was saved as a
  memory on mistral despite the extractor's one-off-action rule — the filter is
  not fully reliable on the weaker model.
- Ambiguous cross-window references (3+ other sessions) are meant to fall back to
  clarify; with two windows "the other window" is unambiguous.
