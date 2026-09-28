# reddit-orchestrator

An autonomous loop that turns Reddit AI/dev discussion into a reviewed, published
Korean blog digest, running local LLMs on a 16GB Mac mini M4.

The predecessor ([reddit-translator](https://github.com/malgcheong/reddit-translator))
runs only when a human clicks. This one runs unattended: it collects, plans,
drafts, gates, judges, asks for approval, publishes, and records evidence of every
run. It is modeled on an 8-stage "request -> plan -> approve -> execute -> QA gate
-> deploy -> evidence" pattern.

The design constraint is the story: **16GB of unified memory**. Instead of one big
model, it routes across small models by role and escalates to an API only for the
hard parts.

## Architecture

- **orchestrator/** (Python, LangGraph + FastAPI): the loop, the model gateway
  (Ollama + MLX), collection, gates, and the LLM judge.
- **dashboard/** (Spring Boot, Java 21): the `/orchestra` run-history dashboard
  (run list, per-step evidence, model success-rate stats) reading the shared
  Postgres read-only via JdbcTemplate + Thymeleaf.
- **Shared Postgres**: run state, per-step evidence, and LangGraph checkpoints.

### Models (roles, not sizes)

| role | model | why |
|---|---|---|
| router / planner | `lfm2.5:8b` (MoE, ~1.5B active) | fits 16GB comfortably, very fast |
| worker (draft / judge) | `qwen3.5:9b` (dense) | quality ceiling at this memory budget |
| light worker | `qwen3.5:4b` | parallel / classification |
| escalation | Claude API (optional) | only when judge confidence is low |

Measured generation speed on this M4: `lfm2.5:8b` 78.8 tok/s, `qwen3.5:4b`
28.0 tok/s, `qwen3.5:9b` 18.1 tok/s. See [docs/benchmark-m4.md](docs/benchmark-m4.md).

## The loop (stages)

```
collect -> plan -> execute -> gate -> judge -> approve -> publish (+ evidence)
            router   worker   code    worker   Discord    Astro/Pages
```

- **plan / judge** use JSON-schema constrained decoding (Ollama `format`), so
  structured output is enforced at decode time, not merely requested.
- **gate** is deterministic code (link / dedup / length / schema / banned-word).
  It fails closed and rejects before the judge is asked.
- **thinking is off** for worker calls: this is a batch pipeline, we want the
  answer in `content`, not tokens spent reasoning.

## Status

Working today: collect / plan / execute / gate / judge run end to end on the M4
with local models, structured outputs enforced, evidence and LangGraph checkpoints
persisted to Postgres.

Collection (stage 2) uses Reddit's public RSS top feed (no credentials): Reddit
now 403s the `.json` endpoints for non-OAuth clients, but the RSS feed still
serves and is already ranked "top of day". Trade-off: no score/comment counts.
Rate limits are handled with backoff, and a failed subreddit degrades gracefully.
Upgrade path is read-only PRAW (client_id/secret only).

Approval (stage 7) is a real human-in-the-loop pause: the graph interrupts at the
approve step (checkpointed to Postgres), sends a Discord preview, and only
continues to publish when a decision arrives. Decide with the resume CLI
(`python -m orchestrator.resume <digest_key> approve|reject`) or, with a bot token,
the interactive Approve/Reject buttons in `discord_bot.py`. No webhook configured
means dry mode (preview prints to console), so the flow is testable without Discord.

The Spring Boot dashboard (`/orchestra`) shows run history, per-step evidence,
and per-model success rate / latency from the same Postgres.

Fully unattended: two launchd agents (daily run + always-on approval bot) under
`scripts/`. See [docs/scheduling.md](docs/scheduling.md) and
[docs/discord-setup.md](docs/discord-setup.md). Enable them once a Discord webhook
or bot is configured.

## Run it

```bash
# prerequisites: Ollama running with the three models pulled, Postgres up
cd orchestrator
uv sync
uv run python -m orchestrator.run              # full run, persists to Postgres
uv run python -m orchestrator.run --no-db      # just the loop, no persistence
uv run python -m orchestrator.run --backend mlx  # use the MLX path

# speed benchmark (Ollama)
python ../scripts/benchmark.py
```

Dashboard (needs JDK 21; Maven otherwise defaults to a newer JDK here):

```bash
cd dashboard
JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home \
  mvn -DskipTests package
java -jar target/orchestra-dashboard-0.1.0.jar   # http://localhost:8095/orchestra
```

Copy `orchestrator/.env.example` to `orchestrator/.env` and fill in Reddit,
Discord, and blog settings when wiring the collect and publish stages.
