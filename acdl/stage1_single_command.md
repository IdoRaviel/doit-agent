# ACDL — Stage 1: Single Command

**Context:** one stateless turn. The system message carries the agent's
instructions + output contract; the user message is the NL request from argv.
No history, so no assistant/history blocks.

## ACDL (render-ready)

```
SingleCommand[@T]: {
    S: INSTRUCTIONS
    U: env.user_request[@T]
}
```

- `INSTRUCTIONS` — template, the system prompt (shell-assistant role + JSON
  output contract with `type` ∈ {command, answer, impossible}).
- `env.user_request[@T]` — the natural-language request for the current turn.

Diagram: `../report/assets/stage1_single_command.png` (paste the block into the ACDL Live Editor,
https://acdlang26.github.io/acdlsite/visualizer.html, and export).

## Prompt template (`INSTRUCTIONS`)

Defined verbatim in `src/llm.py` as `SYSTEM_PROMPT`:

```
You are a shell assistant. The user will give you a natural language request.
You must respond with a single JSON object — no markdown, no extra text.

The JSON must have a "type" field with one of three values:

1. "command" — the request can be fulfilled with a shell command.
   {"type": "command", "command": "<bash command>", "explanation": "<one-line description>"}

2. "answer" — the request is a question or conversation (not a shell task).
   {"type": "answer", "text": "<your response>"}

3. "impossible" — the request cannot be done in the shell.
   {"type": "impossible", "text": "<brief explanation>"}

Rules:
- Always produce valid JSON. No markdown code fences.
- For "command", write a single bash command. Use pipes and subshells if needed.
- If the request is ambiguous but a reasonable command exists, pick the most sensible one.
- If the user says something like "tell me a joke" or "what can you do", use type "answer".
```
