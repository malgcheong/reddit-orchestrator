"""Dry-run the orchestration loop on sample data.

  uv run python -m orchestrator.run              # with Postgres (state + checkpoints)
  uv run python -m orchestrator.run --no-db      # no persistence, just the loop
  uv run python -m orchestrator.run --backend mlx
"""
import argparse
import datetime
import json

from . import db
from .config import settings
from .graph import build_graph
from .sample_data import SAMPLE_POSTS


def _print_report(final: dict):
    plan = final.get("plan") or {}
    gate = final.get("gate") or {}
    judge = final.get("judge") or {}
    print("\n" + "=" * 60)
    print(f"PLAN   : {plan.get('title')}  ({len(plan.get('include', []))} items)")
    print(f"         angle: {plan.get('angle')}")
    print(f"GATE   : {'PASS' if gate.get('passed') else 'REJECT'}")
    for c in gate.get("checks", []):
        print(f"         [{'ok' if c['ok'] else 'XX'}] {c['name']} {c['detail']}")
    if judge:
        print(f"JUDGE  : acc={judge['accuracy']} nonredun={judge['non_redundancy']} "
              f"read={judge['readability']} conf={judge['confidence']}")
        print(f"         {judge['notes']}")
    print("STEPS  :")
    for s in final.get("steps", []):
        model = s.get("model") or "-"
        backend = s.get("backend") or "code"
        intok = s.get("input_tokens") or 0
        outtok = s.get("output_tokens") or 0
        lat = s.get("latency_ms") or 0
        print(f"         {s['stage']:8s} {backend}/{model:14s} "
              f"in={intok:>5} out={outtok:>5} {lat:>6}ms {s['verdict']}")
    print("=" * 60)
    print("\n----- DRAFT -----\n")
    print(final.get("draft", "(none)"))


def _run(graph, digest_key, run_id):
    state = {"digest_key": digest_key, "posts": SAMPLE_POSTS, "run_id": run_id}
    config = {"configurable": {"thread_id": digest_key}}
    return graph.invoke(state, config=config)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="skip Postgres persistence")
    ap.add_argument("--backend", default="ollama", choices=["ollama", "mlx"])
    ap.add_argument("--date", help="override digest date (YYYY-MM-DD)")
    args = ap.parse_args()

    day = args.date or datetime.date.today().isoformat()
    digest_key = f"digest-{day}"

    if args.no_db:
        graph = build_graph()
        final = _run(graph, digest_key, run_id=0)
        _print_report(final)
        return

    from langgraph.checkpoint.postgres import PostgresSaver

    db.init_schema()
    run_id = db.create_run(digest_key, trigger="manual")
    with PostgresSaver.from_conn_string(settings.database_url) as cp:
        cp.setup()
        graph = build_graph(checkpointer=cp)
        final = _run(graph, digest_key, run_id=run_id)

    status = final.get("status", "judged")
    db.save_steps(run_id, final.get("steps", []))
    db.save_digest(run_id, digest_key, final.get("plan"), final.get("draft"),
                   final.get("judge"), status)
    db.finish_run(run_id, status)
    _print_report(final)
    print(f"\n[db] run_id={run_id}  digest_key={digest_key}  status={status}")


if __name__ == "__main__":
    main()
