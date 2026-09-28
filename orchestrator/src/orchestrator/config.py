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

    # Blog publish target (a local clone of the Astro/Fuwari repo; push -> Pages deploy)
    blog_repo_path: str = "/Users/sukyungmac/workspace_side/malgcheong.github.io"
    blog_base_url: str = "https://malgcheong.github.io"
    # On approval, publish writes + commits locally; push (live deploy) stays opt-in.
    blog_auto_push: bool = False

    # Discord approval (stage 7)
    discord_webhook_url: str = ""     # send-only preview; empty -> dry mode (console)
    discord_bot_token: str = ""       # interactive buttons; empty -> use resume CLI
    discord_channel_id: int = 0
    approval_timeout_hours: int = 24

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "reddit-orchestrator/0.1 by u/malgcheong"
    subreddits: list[str] = ["LocalLLaMA", "MachineLearning"]


settings = Settings()
