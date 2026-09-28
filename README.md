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
- **dashboard/** (Spring Boot, planned): the `/orchestra` run-history dashboard,
  Discord approval webhook, and blog publish (commit/push to the Astro repo).
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

Next: Discord approval (stage 7), Astro publish (stage 8), the Spring Boot
dashboard, and a launchd schedule.

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

Copy `orchestrator/.env.example` to `orchestrator/.env` and fill in Reddit,
Discord, and blog settings when wiring the collect and publish stages.
