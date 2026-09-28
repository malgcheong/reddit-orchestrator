from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Ollama (GGUF path, always-resident router/workers)
    ollama_base_url: str = "http://localhost:11434"
    router_model: str = "lfm2.5:8b"
    worker_model: str = "qwen3.5:9b"
    light_model: str = "qwen3.5:4b"

    # MLX (Apple-native path, benchmarked head-to-head against Ollama)
    mlx_model: str = "mlx-community/Qwen3.5-9B-Instruct-4bit"

    # Escalation API (optional; used only when judge confidence is low)
    anthropic_api_key: str = ""

    # Postgres
    database_url: str = "postgresql://orchestrator:orchestrator@localhost:5432/orchestrator"

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "reddit-orchestrator/0.1"


settings = Settings()
