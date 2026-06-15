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
- **Success/failure feedback**: many commands (touch, rm, mkdir, cd) are silent
  on success, which left the user with no confirmation after a `y`. We print
  `✓ done` when a command succeeds with no output, and `✗ exited with code N`
  on nonzero exit (and still propagate the exit code).
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

## Model flexibility

- Hosted: `gemini/gemini-2.5-flash` (free tier; 2.0-flash hit a `limit: 0` quota
  issue on a fresh project, hence 2.5).
- Local no-tool: `ollama/llama3:8b`.
- Local tool-calling: `ollama/mistral:7b`.
- No model-specific code. LiteLLM is the only thing that talks to a model
  (`src/llm.py`), and it routes on the `provider/` prefix of the config string:
  `gemini/*` → Google's hosted API (key from `~/doit.cfg`); `ollama/*` → the local
  Ollama daemon over HTTP at `localhost:11434`. Switching models is a one-line
  edit in `~/doit.cfg`, no code change — the assignment's "easy to switch" goal.
- No ACDL artifact for this section: the context is identical to Stage 2; only
  the model string changes.

---

## Stage 3 — Multi-turn

### Assignment questions

- **How/where do you store the history?** Append-only JSON Lines at
  `~/.doit/history.jsonl` (hidden state dir). Each run appends ONE record after
  acting: timestamp, request, `type`, command + explanation, and execution result
  (stdout/stderr/returncode/`executed`). JSONL because every invocation is a
  fresh process — appending a line and tailing the last N is cheap, no rewrite.
  Each record also tags the `model` that produced it — metadata ONLY (for log/
  report traceability); it is NOT fed into the context and does NOT filter what
  history a model sees. History is task-scoped, not model-scoped: which model
  wrote a prior turn is irrelevant to resolving "now sort them".
  (One global stream for now; per-terminal separation is the multi-tasking stage.)
- **How do you present history to the LLM?** Replay the last `MAX_TURNS=8` turns
  as real user/assistant message pairs before the current request
  (`history.build_messages`). User msg = old request; assistant msg = a *rendered
  view* (`_replay_assistant`): for a command, `Ran: <cmd>` + 1000-char-clipped
  output tail + exit code; for answer/impossible, the text. Clipping bounds
  context; the 8-turn window bounds drift.
- **Distinguish new vs. referring commands, and which one?** Deliberately NO
  separate classifier. We feed bounded recent history and let the model decide if
  the request is fresh or a reference and which prior turn it points at; the
  system prompt's "conversation context" note licenses this. Rationale: a hard
  "is this a follow-up?" gate is brittle on indirect references; replaying real
  turns is simpler and degrades gracefully.

### Design decisions

- Replay as readable assistant text (not raw stored JSON): keeps the transcript
  legible and lets the model reason over prior *outputs*, which also sets up the
  later output-awareness stage.
- Record EVERY outcome — executed command, aborted command (`executed: false`),
  answer, impossible — so the next turn sees a complete trace.

### Model comparison (4-turn seq: list → "sort by size largest first" →
### "no, smallest first" → "what can you do?")

- All three emitted parseable JSON (no fallback), chose the right `type` each turn
  (`answer` for T4), and resolved the follow-up references. The divergence was in
  COMMAND QUALITY/LOGIC, not format.
- **gemini-2.5-flash**: simplest + correct — `ls` / `ls -S` / `ls -Sr`.
- **mistral:7b (tool-trained)**: correct — `ls` / `ls -lS` / `ls -lS | tail -n +2
  | sort -h`. Clean reference resolution.
- **llama3:8b (NOT tool-trained) — the failure case**: format was fine (valid
  JSON, right `type`, tracked the references), but the *command* was wrong twice:
  1. **Inverted logic** — for "largest first" it used `ls -lSr`; `-r` reverses, so
     that's *smallest* first.
  2. **Bad shell** — `ls -lSr | grep ^- | cut -d' ' -f9-`; `cut -d' '` splits on a
     single space but `ls -l` pads with runs of spaces, so output was garbled
     (truncated names, multi-word PDF name split). On T3 it just appended `| tac`,
     compounding the error.
  Takeaway: llama3 understood *what kind* of response and produced the right JSON
  shape, but generated a lower-quality, logically-inverted command. Mistral
  produced correct minimal commands.
  Caveat: single easy run; llama3's JSON happened to be clean here. The classic
  non-tool failure (prose / fenced JSON needing our fallback) didn't trigger but
  is likely on harder prompts — probe again later.

---

## Stage — Clarifications  *(in progress)*

- Implemented as a FOURTH response type, `clarify`, not as a native tool:
  `{"type": "clarify", "question": "...", "options": [...]}`. doit prints the
  question + numbered options, reads an answer, then re-calls the model with the
  Q&A appended and handles the result (normally a command).
- **Why not a native tool (the report point):** the assignment hints the question
  "can be represented as a tool" if using tool calling. We don't, for the SAME
  reason as the cross-cutting structured-JSON decision: native tool-calling does
  not work on the no-tool local model (llama3:8b), so it would split our code
  path by provider. Keeping `clarify` as one more `type` in the single JSON
  contract means clarifications work identically across all three required models
  with no per-model branching. So `command/answer/impossible/clarify` are four
  shapes of ONE response, not four tools.
- "Only when needed" tuning lives in the prompt: prefer a sensible default;
  reserve `clarify` for genuine forks where the choice materially changes the
  command (e.g. creation vs. access date), not trivial ambiguity.
- No-answer handling: NEVER guess. Wait up to `CLARIFY_TIMEOUT=120s` (select-based
  timed read on stdin), then exit cleanly with a message; record an unanswered
  clarify turn. Bounded at `MAX_CLARIFY=3` rounds.
- DONE & tested (answered + no-answer paths). ACDL: acdl/stage4_clarifications.md.

---

## Stage 5 — Richer interactions

- PROMPT-ONLY change (no scheme change; same context as Stage 4). Two new
  behaviours: (a) "how do I…" questions → `answer` that EXPLAINS + suggests the
  command in backticks WITHOUT executing; (b) follow-ups resolved from replayed
  history — "execute it"/"run it"/"do it" → `command`; "modify it to …" keeps the
  same mode (a suggestion stays an `answer`; an executed command stays a
  `command`).
- "it" in "modify it" = the previously suggested/run command; the model tells the
  two apart because the replay shows executed commands as `Ran: <cmd>` vs an
  answer's plain suggestion text.
- **Rules alone were not enough for mistral** — it kept turning "modify it" into a
  command. Adding a one-shot example to the prompt fixed it; gemini followed the
  rules without the example. (Weak instruction model needs examples, not just
  rules — recurring theme.)
- Bug fixed here: dangerous-command `Proceed?` used bare `input()` → crashed with
  EOFError on closed stdin; now caught and treated as "no" (abort).
- DONE & tested (mistral before/after example, gemini). ACDL:
  acdl/stage5_richer_interactions.md. Runs: report/stage5_richer_interactions_runs.md.

---

## Stage 6 — Memory

- Memory = durable facts/preferences in `~/.doit/memory.jsonl`, separate from
  per-turn history; survives new terminals/dirs/sessions. Injected into the system
  prompt every turn so the model can recall/act on them.
- **Orthogonal, not a type.** A turn can both act AND record a memory, so memory
  is NOT a response type. (Tried a `memory_candidate` field on the main response;
  weak models either made it a bogus `type` value or dropped the key.)
- **Dedicated extraction call (always-run).** A second focused call decides
  save/skip + condenses, every turn. Chosen over a gated approach because gating
  depends on the weak main model flagging a candidate, which it does unreliably —
  so the dedicated call owns the decision. Cost: +1 call/turn.
- **Dedup by passing memories to the extractor.** The extractor sees "Already
  known: ..." and returns save:false for facts already stored. This replaced a
  brittle code-side token-similarity dedup (user's call: "just pass the memories").
  Fixed a duplicate-on-recall bug where asking about a fact re-saved a paraphrase.
- Decision journey worth reporting: gated→always-run (weak model can't flag);
  field-on-response→separate call (weak model drops orthogonal key); code-dedup→
  pass-memories-to-extractor (semantic, simpler).
- Bugs fixed here: weak model invented `{"type":"memory"}` → added "type must be
  one of the four" rule + graceful dispatch fallback; rate-limit errors now print
  a clean message instead of raw 429 JSON.
- **Limitations:** (1) factual recall works on all tested models; behavioural
  preferences ("ask me each time") are shaky on mistral — misread as act-now,
  not stored, not honoured. (1b) the COMBINED action+memory request is the hardest
  case: on it each local model nailed only one half — mistral saved the memory but
  only suggested the action; llama3 ran the action but didn't save the memory.
  (2) memory list injected into BOTH main + extractor
  prompts grows with count — retrieval/summarization is a candidate extension.
  (3) `cd` in a subprocess doesn't change the user's shell dir (user-awareness/
  multi-tasking stages). (4) gemini memory run blocked by daily free-tier quota.
- DONE on local models. ACDL: acdl/stage6_memory.md. Runs:
  report/stage6_memory_runs.md.

---

## Parking lot / TODO for later stages

- User-awareness, output-awareness, multi-tasking, +1 extension — add a section
  each as built.
