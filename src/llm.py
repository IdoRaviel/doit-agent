import json
import re

import litellm

SYSTEM_PROMPT = """\
You are a shell assistant. The user will give you a natural language request.
You must respond with a single JSON object — no markdown, no extra text.

The JSON must have a "type" field with one of three values:

1. "command" — the request can be fulfilled with a shell command.
   {"type": "command", "command": "<bash command>", "explanation": "<one-line description>", "safe": <true|false>}
   Set "safe" to false if the command modifies the system: creates, moves,
   deletes, or overwrites files; changes permissions/ownership; formats disks;
   or rewrites git state. Set "safe" to true for read-only commands that only
   display information (ls, cat, grep, find, ps, df, etc.).

2. "answer" — the request is a question or conversation (not a shell task).
   {"type": "answer", "text": "<your response>"}

3. "impossible" — the request cannot be done in the shell.
   {"type": "impossible", "text": "<brief explanation>"}

Rules:
- Always produce valid JSON. No markdown code fences.
- For "command", write a single bash command. Use pipes and subshells if needed.
- If the request is ambiguous but a reasonable command exists, pick the most sensible one.
- If the user says something like "tell me a joke" or "what can you do", use type "answer".
"""


def ask(user_request: str, model: str) -> dict:
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_request},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    return _parse(raw)


def _parse(raw: str) -> dict:
    # Strip markdown code fences if the model ignores instructions
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: treat the whole response as a plain answer
        return {"type": "answer", "text": raw}

    if "type" not in data:
        return {"type": "answer", "text": raw}

    return data
