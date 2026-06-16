# Stage 8 — Output awareness: experiment outputs

Works with NO new code: the prior command's stdout/stderr/exit code are already
stored and replayed (multi-turn history). Verified on both local models.

## Explain a real failure (from stored stderr)
```
T1  $ doit "show the contents of /etc/sudoers"   -> cat /etc/sudoers; "Permission denied"; exit 1
T2  $ doit "why did that fail?"
mistral: failed because you don't have read access to /etc/sudoers; try `sudo cat /etc/sudoers`.
llama3:  the cat command failed for lack of permissions to read /etc/sudoers; exit code 1 = permission error.
```

## Reason over prior stdout
```
T1  $ doit "show the 5 largest files here"   -> ls -lh | sort -hr | head -n 5
T2  $ doit "which of these looks safe to delete?"
mistral: picks doit.cfg.example (small, an example config), suggests backing up first.
llama3:  suggests logs/requirements.txt/tests, keep doit.cfg.example/README (reasoning is shaky but uses the real listing).
```

Both models handle output awareness — because the output is ALREADY in context
(push), no tool-call decision is required. Contrast Stage 7, where llama3 failed
the shell-history TOOL (pull) because it had to decide to call it.

## Limitation found + fixed: aborted commands
"why did that fail?" after an ABORTED dangerous command first hallucinated a
reason (it was never run). Prompt now states a "Proposed (not run)" command was
not executed:
```
T1  $ doit "delete everything in this directory"  -> rm -rf * (dangerous; aborted, not run)
T2  $ doit "why did that fail?"
    "The proposed command would delete all files recursively ... I won't execute it without
     confirmation. ... type 'execute it' ..."   (correctly: not run, not a failure)
```
