import json

from ..config import settings
from .base import ChatResult
from .mlx_backend import MlxBackend
from .ollama_backend import OllamaBackend

# Role -> Ollama model. The design draft's role split: a fast MoE router and
# heavier dense workers.
ROLE_MODELS = {
    "router": settings.router_model,   # lfm2.5:8b   - plan / route / extract
    "worker": settings.worker_model,   # qwen3.5:9b  - summarize / draft / judge
    "light": settings.light_model,     # qwen3.5:4b  - parallel / classify
}


class Gateway:
    """Backend-agnostic entry point. `backend="ollama"` (default) or `"mlx"`."""

    def __init__(self):
        self.ollama = OllamaBackend(settings.ollama_base_url)
        self._mlx = None

    def _mlx_backend(self) -> MlxBackend:
        if self._mlx is None:
            self._mlx = MlxBackend(settings.mlx_model)
        return self._mlx

    def _resolve(self, role: str, backend: str):
        if backend == "mlx":
            return self._mlx_backend(), settings.mlx_model
        return self.ollama, ROLE_MODELS[role]

    def generate(self, role, messages, json_schema=None, backend="ollama", options=None) -> ChatResult:
        be, model = self._resolve(role, backend)
        return be.chat(model, messages, json_schema=json_schema, options=options)

    def generate_json(self, role, messages, schema_model, backend="ollama", options=None):
        """Return (validated pydantic object, ChatResult)."""
        schema = schema_model.model_json_schema()
        res = self.generate(role, messages, json_schema=schema, backend=backend, options=options)
        text = res.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
        obj = schema_model.model_validate_json(text)
        return obj, res
