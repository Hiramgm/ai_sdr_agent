from __future__ import annotations

import json
import re
from typing import Any

from ai_sdr.config import SETTINGS, Settings


def _extract_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if match is None:
            raise ValueError(f"Groq response did not contain JSON: {content}") from None
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Groq JSON response must be an object.")
    return parsed


def complete_json(
    system_prompt: str,
    user_prompt: str,
    settings: Settings = SETTINGS,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> dict[str, Any]:
    """Ask Groq for a JSON object and parse the result."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required for LLM agent decisions.")

    try:
        from groq import Groq
    except ImportError as error:
        raise RuntimeError(
            "Install the Groq SDK before running the LLM workflow: "
            ".venv/bin/python -m pip install -r requirements.txt"
        ) from error

    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return _extract_json_object(content)

