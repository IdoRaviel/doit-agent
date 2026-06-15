# doit — Design Notes (raw material for the report)

> Running scratchpad of design decisions, rationale, trade-offs, and "why" behind
> each stage. Not the final report — this is the bullet source we draw from when
> writing `report/report.md`. Add to it *as we build*, while the reasoning is fresh.

---

## Cross-cutting decisions (apply to the whole agent)

- **Structured JSON output instead of native tool-calling.** The model returns a
  single JSON object with a `type` field; our code parses and routes it. Why:
  - **Portability across the three required models.** The assignment requires a
    hosted API model, a local model *with* tool-calling, and a local model
    *without* tool-calling. Native tool-calling would not work on the no-tool
    local model (e.g. `llama3:8b`). A plain-text JSON contract works on all three
    with one prompt, so we get one code path instead of branching per provider.
  - **Control over parsing & fallback.** We own the parse step, so we can repair
    or retry malformed output — important because local models are shakier at
    emitting clean JSON than hosted ones (a point we'll demonstrate in the model
    comparison).
  - **Transparency for the report/ACDL.** The exact context sent to the model is
    just text we wrote, easy to document in ACDL and show verbatim.
- **One generic "shell command" action, not per-command tools.** We do not expose
  `ls`, `grep`, `git`, … as separate tools. The model emits an arbitrary bash
  command string and we execute it. Why: matches the assignment's explicit hint
  ("you generally do not want to implement each command as a separate tool"),
  keeps the tool surface tiny, and lets the model use pipes/subshells freely.
- **Model selection via `~/doit.cfg`.** LiteLLM model string in
  `provider/model-name` form; `src/config.py` reads it fresh every invocation, so
  switching models is a one-line edit with no restart. API key only needed for
  hosted providers; ignored for `ollama/*`.
- **LiteLLM as the provider abstraction.** Swapping hosted ↔ local is just the
  config string; no code change. (Reason the assignment mandates LiteLLM.)

---

## Stage 1 — Single command

- **Three response types routed by a `type` field**: `command`, `answer`,
  `impossible`. This directly answers the assignment's "the model may need to
  produce a command, a regular answer, or an explanation that it can't be done"
  — we recognize the case from `type` and handle each.
  - `command` → show command, execute, show output.
  - `answer` → chit-chat / "what can you do" / "tell me a joke" handled nicely.
  - `impossible` → explain why it can't be a shell command.
- **Output capture**: `subprocess.run` with `capture_output`, `text=True`, and a
  timeout; we keep stdout, stderr, and returncode (per the assignment's snippet).
- Limitation to note in report: single stateless turn, no memory yet.

---

## Stage 2 — Dangerous commands

- **Dual safety gate (defense-in-depth).** A command auto-runs only if BOTH:
  1. the LLM tagged it `"safe": true` in the JSON, AND
  2. the local regex backstop in `src/safety.py` finds no destructive pattern.
  Otherwise we show the command + explanation and require an explicit `y`.
- **Why two layers and not just the LLM flag.** We don't want to trust the model
  alone for a safety-critical decision — it can mislabel a destructive command as
  safe. The regex backstop is a deterministic, auditable second opinion that
  catches the obvious destructive cases (`rm`, `mv`, `>`, `chmod`, `dd`, git
  history rewrites, …) regardless of what the model claims.
- **Why the gate lives in code, not in the LLM context.** The ACDL/context is
  unchanged from Stage 1 except the `INSTRUCTIONS` template now asks for a `safe`
  field. The decision logic (auto-run vs. confirm) is program logic, kept out of
  the prompt on purpose — keeps the context simple and the safety behavior
  deterministic.
- Limitation to note: regex backstop is heuristic (possible false positives on
  exotic-but-safe commands, and it can't understand intent); the `y` gate is the
  real safety net.

---

## Stage 3 — Model flexibility  *(in progress)*

- Hosted: `gemini/gemini-2.5-flash` (free tier; 2.0-flash hit a `limit: 0` quota
  issue on a fresh project, hence 2.5).
- Local no-tool: `ollama/llama3:8b`.
- Local tool-calling: `ollama/mistral:7b`.
- (TODO) Record: which models reliably emit clean JSON, where the no-tool model
  needed different prompting, failure/recovery examples for the comparison.

---

## Parking lot / TODO for later stages

- Multi-turn, clarifications, richer interactions, memory, user-awareness,
  output-awareness, multi-tasking, +1 extension — add a section each as built.
