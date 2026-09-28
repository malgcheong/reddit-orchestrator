from dataclasses import dataclass


@dataclass
class ChatResult:
    text: str
    model: str
    backend: str          # ollama | mlx
    input_tokens: int
    output_tokens: int
    latency_ms: int
