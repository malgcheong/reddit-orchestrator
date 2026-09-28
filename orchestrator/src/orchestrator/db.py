import json
from pathlib import Path

import psycopg

from .config import settings

# repo_root/db/migration/V1__init.sql  (this file: repo_root/orchestrator/src/orchestrator/db.py)
MIGRATION = Path(__file__).resolve().parents[3] / "db" / "migration" / "V1__init.sql"


def connect():
    return psycopg.connect(settings.database_url)


def init_schema():
    sql = MIGRATION.read_text()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()


def create_run(digest_key: str, trigger: str = "manual") -> int:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into runs(digest_key, trigger) values (%s, %s) "
            "on conflict (digest_key) do update set status='running', "
            "started_at=now(), finished_at=null returning id",
            (digest_key, trigger))
        rid = cur.fetchone()[0]
        conn.commit()
        return rid


def finish_run(run_id: int, status: str):
    with connect() as conn, conn.cursor() as cur:
        cur.execute("update runs set status=%s, finished_at=now() where id=%s", (status, run_id))
        conn.commit()


def save_steps(run_id: int, steps: list[dict]):
    with connect() as conn, conn.cursor() as cur:
        for s in steps:
            cur.execute(
                "insert into run_steps(run_id, stage, model, backend, input_tokens, "
                "output_tokens, latency_ms, verdict, detail) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (run_id, s["stage"], s.get("model"), s.get("backend"),
                 s.get("input_tokens"), s.get("output_tokens"), s.get("latency_ms"),
                 s.get("verdict"), json.dumps(s.get("detail", {}))))
        conn.commit()


def save_digest(run_id: int, digest_key: str, plan: dict, draft: str, judge: dict, status: str):
    title = plan.get("title") if plan else None
    score = None
    if judge:
        score = round((judge["accuracy"] + judge["non_redundancy"] + judge["readability"]) / 3, 2)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into digests(run_id, digest_key, title, markdown, status, judge_score) "
            "values (%s,%s,%s,%s,%s,%s) "
            "on conflict (digest_key) do update set title=excluded.title, "
            "markdown=excluded.markdown, status=excluded.status, judge_score=excluded.judge_score",
            (run_id, digest_key, title, draft, status, score))
        conn.commit()
