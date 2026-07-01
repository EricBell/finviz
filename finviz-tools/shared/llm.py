"""Small helper for LLM-based request interpretation.

Supports any OpenAI-compatible chat completions endpoint, including local
Ollama servers exposed at /v1/chat/completions.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str | None
    timeout: int


def get_config() -> LLMConfig:
    base_url = os.environ.get("FINVIZ_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.environ.get("FINVIZ_LLM_MODEL", "llama3.1")
    api_key = os.environ.get("FINVIZ_LLM_API_KEY")
    timeout = int(os.environ.get("FINVIZ_LLM_TIMEOUT", "60"))
    return LLMConfig(base_url=base_url, model=model, api_key=api_key, timeout=timeout)


def _extract_json(text: str) -> Any:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, flags=re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise LLMError("Model response did not contain valid JSON")


def chat_json(*, system: str, user: str, model: str | None = None) -> Any:
    cfg = get_config()
    payload = {
        "model": model or cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    url = f"{cfg.base_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=cfg.timeout) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raise LLMError(f"LLM request failed: {exc.code} {exc.reason}") from exc
    except error.URLError as exc:
        raise LLMError(f"LLM request failed: {exc.reason}") from exc

    parsed = json.loads(body)
    content = parsed["choices"][0]["message"]["content"]
    return _extract_json(content)
