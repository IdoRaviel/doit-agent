# `doit` — an interactive LLM shell agent

`doit` turns natural language into shell commands. You describe what you want, it
shows the command it intends to run, runs it (asking first if the command is
destructive), and reports the output.

```console
$ doit "list the files in my Documents folder"
# Lists files in ~/Documents
ls ~/Documents

report.pdf  notes.md  budget.xlsx
```

It is more than a one-shot translator. `doit` remembers the conversation across
invocations, asks for clarification when a request is genuinely ambiguous, answers
"how do I…" questions without running anything, keeps durable memories about you,
and works across a hosted API model and local models alike.

> Built for an LLM course assignment on agents. The implementation prioritises
> clean context management and a single code path that works across very different
> models.

---

## Features

- **Natural language → shell command**, shown before it runs.
- **Safety gate** — read-only commands run directly; anything that modifies the
  system is explained and requires a `y` confirmation. A model judgement *and* a
  local regex check must both agree before auto-running.
- **Three response modes** — run a command, answer a question, or explain that a
  request isn't a shell task; plus a fourth, **clarify**, when genuinely unsure.
- **Multi-turn memory** — follow-ups like `"now sort them by size"` or
  `"no, smallest first"` resolve against previous turns.
- **Clarifications** — asks a question (with options) when ambiguous, waits up to
  two minutes, and never guesses.
- **Richer interactions** — `"how do I…"` gets an explanation (not an execution);
  `"execute it"` then runs it; `"modify it to…"` updates the suggestion.
- **Persistent memories** — durable facts/preferences (e.g. your project folder)
  survive new terminals and sessions.
- **Model flexibility** — switch between a hosted API model and local models with a
  one-line config change; no code change.

## How it works (in one paragraph)

`doit` does **not** use a provider's native tool-calling. The model returns a
single JSON object (a `type` plus fields), which the program parses and acts on.
This keeps one code path working across all three required model classes — a
hosted API model, a local model *with* tool support, and a local model *without*
it — and is reached through [LiteLLM](https://github.com/BerriAI/litellm), so the
provider is just a config string.

---

## Requirements

- **Python 3.10+**
- **Linux or macOS** (bash/zsh). On Windows, use WSL or Git Bash.
- A model to talk to — either:
  - a **hosted API key** (e.g. Google AI Studio / Gemini, free tier), and/or
  - **[Ollama](https://ollama.com)** for local models.

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <your-repo-url> doit-agent
cd doit-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Point the `doit` launcher at your environment

`doit` is a Python script whose first line (the shebang) points to the virtual
environment's interpreter. Update it to your clone's path:

```bash
# first line of ./doit should be the absolute path to your venv python, e.g.:
#!/ABSOLUTE/PATH/TO/doit-agent/.venv/bin/python3
```

Then make it executable:

```bash
chmod +x doit
```

### 3. Add `doit` to your PATH

So you can run `doit` from any directory. Add this to `~/.bashrc` (or `~/.zshrc`):

```bash
export PATH="$PATH:/ABSOLUTE/PATH/TO/doit-agent"
```

Reload your shell: `source ~/.bashrc` (or open a new terminal).

### 4. Create the config file `~/doit.cfg`

This single file selects which model `doit` uses.

```bash
cp doit.cfg.example ~/doit.cfg
```

Then edit `~/doit.cfg` and set the model (and API key if hosted):

```ini
[model]
name = gemini/gemini-2.5-flash    # provider/model in LiteLLM format
api_key = YOUR_API_KEY_HERE       # not needed for ollama/* models
```

### 5. (Optional) Set up local models with Ollama

For the local model classes (and to run with no API key / no network):

```bash
# install Ollama from https://ollama.com, then:
ollama pull mistral:7b     # a tool-calling model
ollama pull llama3:8b      # a strong instruction model without tool-calling
```

Ollama runs a local server automatically; `doit` reaches it via LiteLLM at the
default `http://localhost:11434`.

### 6. (Optional) Enable shell-history awareness

So `doit` can answer "what did I just do?" using your *recent* commands, let bash
flush history after each command. Add to `~/.bashrc` (or `~/.zshrc`):

```bash
export PROMPT_COMMAND='history -a'
```

Without this, bash only writes `~/.bash_history` on shell exit, so the most recent
in-session commands may be missing. (`doit`'s own commands run via subprocess and
never enter your shell history, so they stay separate from your manual commands.)

**Multi-terminal sessions** work out of the box — `doit` derives a per-terminal
session id from the launching shell, so each window keeps its own history stream.
If you want a stable, explicit id (e.g. it survives a shell restart), add:

```bash
export DOIT_SESSION="$$"   # or any per-terminal value
```

### 7. Verify

```bash
doit "what can you do?"
doit "list the files here"
```

---

## Choosing / switching models

Edit the `name` line in `~/doit.cfg` — no restart, no code change:

| To use | `name =` |
|---|---|
| Hosted API (Google Gemini) | `gemini/gemini-2.5-flash` |
| Local, tool-calling | `ollama/mistral:7b` |
| Local, no tool-calling | `ollama/llama3:8b` |

The `api_key` line is only read for hosted providers; it is ignored for `ollama/*`.

---

## Usage examples

```bash
# A command (runs read-only directly)
doit "show the 5 largest files here"

# A destructive command (asks first)
doit "delete all .tmp files"        # -> shows command, explains, waits for y

# A follow-up (uses conversation history)
doit "now only the ones bigger than 1MB"

# A question (answers, does not run anything)
doit "how do I find files changed today?"
doit "execute it"                   # now it runs the suggested command

# A durable memory (persists across terminals)
doit "remember that my notes live in ~/notes"
doit "open my notes folder"         # later, even in a new terminal
```

---

## Where state lives

| Path | What |
|---|---|
| `~/doit.cfg` | Model selection + API key (the only visible file) |
| `~/.doit/history.jsonl` | Multi-turn conversation history |
| `~/.doit/memory.jsonl` | Durable memories about you |

`~/.doit/` is a hidden directory holding all runtime state.

---

## Project layout

```
doit-agent/
├── doit                 # the CLI launcher (Python)
├── src/                 # config, llm, shell, safety, history, memory
├── doit.cfg.example     # sample config to copy to ~/doit.cfg
├── requirements.txt
├── acdl/                # ACDL context descriptions + rendered diagrams
└── report/              # design notes + per-stage experiment run logs
```

---

## Status

Implemented: single command, safety gate, model flexibility, multi-turn,
clarifications, richer interactions, and persistent memory. Planned next:
user-awareness (reading your shell history), output-awareness, multi-terminal
sessions, and a further agent extension.
