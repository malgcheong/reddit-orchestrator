-- Shared schema for the orchestrator. Applied by the Python service on startup
-- and by the Spring Boot dashboard via Flyway (same file, Flyway naming).

create table if not exists runs (
  id          bigserial primary key,
  digest_key  text not null unique,          -- digest-YYYY-MM-DD (idempotency key)
  status      text not null default 'running',-- running|judged|approved|published|rejected|failed
  trigger     text,                           -- schedule|manual
  started_at  timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists posts (
  id           bigserial primary key,
  run_id       bigint references runs(id) on delete cascade,
  reddit_id    text not null,
  subreddit    text not null,
  title        text not null,
  url          text,
  score        int default 0,
  num_comments int default 0,
  body         text,
  created_utc  timestamptz,
  collected_at timestamptz not null default now(),
  unique (run_id, reddit_id)
);

create table if not exists digests (
  id            bigserial primary key,
  run_id        bigint references runs(id) on delete cascade,
  digest_key    text not null unique,
  title         text,
  markdown      text,
  status        text not null default 'draft', -- draft|gated|judged|approved|published|rejected
  judge_score   numeric,
  approved_by   text,
  published_url text,
  created_at    timestamptz not null default now()
);

-- Per-step evidence: the observability backbone (design draft section 9).
create table if not exists run_steps (
  id            bigserial primary key,
  run_id        bigint references runs(id) on delete cascade,
  stage         text not null,               -- collect|plan|execute|gate|judge|approve|publish
  model         text,
  backend       text,                        -- ollama|mlx|api
  input_tokens  int,
  output_tokens int,
  latency_ms    int,
  cost_usd      numeric default 0,
  verdict       text,                        -- pass|fail|escalate|ok
  detail        jsonb,
  created_at    timestamptz not null default now()
);

create index if not exists idx_run_steps_run on run_steps(run_id);
create index if not exists idx_posts_run on posts(run_id);
