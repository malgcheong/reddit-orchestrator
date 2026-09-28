import time

from .base import ChatResult


class MlxBackend:
    """Apple-native path via mlx-lm. Model is loaded once and cached.

    Note: this backend does plain generation. JSON-schema constrained decoding is
    the Ollama backend's job, so the router sends structured tasks there. MLX is
    used for free-form generation and for the GGUF-vs-MLX speed benchmark.
    """

    name = "mlx"

    def __init__(self, default_model: str):
        self.default_model = default_model
        self._cache = {}

    def _load(self, model: str):
        if model not in self._cache:
            from mlx_lm import load
            self._cache[model] = load(model)
        return self._cache[model]

    def chat(self, model, messages, json_schema=None, options=None, timeout=600) -> ChatResult:
        from mlx_lm import generate
        mdl, tok = self._load(model)
        prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        max_tokens = (options or {}).get("num_predict", 512)

        t0 = time.time()
        text = generate(mdl, tok, prompt=prompt, max_tokens=max_tokens, verbose=False)
        latency_ms = int((time.time() - t0) * 1000)

        return ChatResult(
            text=text.strip(),
            model=model,
            backend=self.name,
            input_tokens=len(tok.encode(prompt)),
            output_tokens=len(tok.encode(text)),
            latency_ms=latency_ms,
        )
