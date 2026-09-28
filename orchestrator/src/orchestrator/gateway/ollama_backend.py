import time

import httpx

from .base import ChatResult


class OllamaBackend:
    """GGUF path via Ollama. Supports JSON-schema constrained decoding by passing
    the schema in the `format` field (llama.cpp grammar under the hood)."""

    name = "ollama"

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def chat(self, model, messages, json_schema=None, options=None, think=False, timeout=600) -> ChatResult:
        # think=False: this is a batch pipeline with constrained outputs; we want the
        # answer in `content`, not tokens spent in a `thinking` field.
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": options or {"temperature": 0.2},
        }
        if json_schema is not None:
            payload["format"] = json_schema

        t0 = time.time()
        r = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        d = r.json()
        return ChatResult(
            text=d["message"]["content"],
            model=model,
            backend=self.name,
            input_tokens=d.get("prompt_eval_count", 0),
            output_tokens=d.get("eval_count", 0),
            latency_ms=int((time.time() - t0) * 1000),
        )
