# Stage 3 — Multi-turn: experiment outputs

Captured runs from the multi-turn / model-flexibility experiments. Each model ran
the SAME 4-turn sequence in the project root, with `~/.doit/history.jsonl` reset
between models so one model's history doesn't leak into another's:

1. `doit "list the files in this directory"`
2. `doit "now sort them by size, largest first"`   (follow-up reference)
3. `doit "no, smallest first"`                      (correction reference)
4. `doit "what can you do?"`                         (non-command)

---

## gemini/gemini-2.5-flash (hosted)

```
T1  # List files and directories in the current directory.
    ls
T2  # List files in the current directory, sorted by size with the largest first.
    ls -S
T3  # List files in the current directory, sorted by size (smallest first).
    ls -Sr
T4  (answer) I can help you with shell commands! Tell me what you want to do, and
    I'll provide the command, an explanation, and tell you if it's safe to run...
```
Commands recorded in history: `ls`, `ls -S`, `ls -Sr`.

## ollama/mistral:7b (local, tool-calling)

```
T1  # Lists all files in the current directory.
    ls
T2  # List files in the current directory sorted by size (largest first)
    ls -lS
T3  # Sorts the files by size in ascending order (smallest first)
    ls -lS | tail -n +2 | sort -h
T4  (answer) I can execute shell commands, manage files and directories, navigate
    the file system, interact with processes, and provide information...
```
Commands recorded in history: `ls`, `ls -lS`, `ls -lS | tail -n +2 | sort -h`.

## ollama/llama3:8b (local, NOT tool-calling)

```
T1  # List files in the current directory
    ls
T2  # List files in this directory, sorted by size (largest first)
    ls -lSr | grep ^- | cut -d' ' -f9-
    -> garbled output: "375 Jun 15 14:46 doit.cfg.example", filenames truncated,
       multi-word PDF name split
T3  # List files in this directory, sorted by size (smallest first)
    ls -lSr | grep ^- | cut -d' ' -f9- | tac
T4  (answer) I can run shell commands, answer questions, and provide information
    about previous turns. I can also help with file management, sorting...
```
Commands recorded in history: `ls`, `ls -lSr | grep ^- | cut -d' ' -f9-`,
`ls -lSr | grep ^- | cut -d' ' -f9- | tac`.

---

## Difference between the model responses

- **All three**: emitted parseable JSON (no fallback), chose the right `type`
  every turn (`answer` for T4), and resolved the T2/T3 follow-up references to the
  prior listing. The divergence was in COMMAND QUALITY / LOGIC, not JSON format.
- **gemini**: simplest and correct (`ls -S` / `ls -Sr`).
- **mistral (tool-trained)**: correct, and resolved T3 with a sensible
  `sort -h` pipeline.
- **llama3 (not tool-trained) — failure case**: format was fine (valid JSON,
  right type, tracked the references) but the COMMAND was wrong twice:
  1. **Inverted logic** — for "largest first" it used `ls -lSr`; `-r` reverses,
     so that is *smallest* first.
  2. **Bad shell** — `ls -lSr | grep ^- | cut -d' ' -f9-`; `cut -d' '` splits on a
     single space but `ls -l` pads with runs of spaces, so the output came out
     garbled. On T3 it just appended `| tac`, compounding the error.

**Takeaway:** llama3 understood *what kind* of response to give and produced the
right JSON shape, but generated a lower-quality, logically-inverted command.
Mistral produced correct, minimal commands.

**Caveat:** single easy run; llama3's JSON happened to be clean here. The classic
non-tool failure (prose / fenced JSON needing our fallback) did not trigger on
these prompts but is likely on harder ones — worth re-probing later.
