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
    print(f"COLLECT: {len(final.get('posts', []))} posts")
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


def _maybe_publish(args, digest_key, day, final, use_db):
    if not args.publish:
        return
    if not final.get("gate", {}).get("passed"):
        print("\n[publish] skipped: gate did not pass")
        return
    from . import publish as pub
    result = pub.publish(digest_key, final["plan"], final["draft"], day, push=args.push)
    print(f"\n[publish] {result}")
    if use_db and result.get("committed"):
        db.mark_published(digest_key, result.get("url", ""),
                          "published" if result.get("pushed") else "approved")


def _run(graph, digest_key, run_id, seed_posts=None):
    state = {"digest_key": digest_key, "run_id": run_id}
    if seed_posts is not None:
        state["posts"] = seed_posts   # skip live collection
    config = {"configurable": {"thread_id": digest_key}}
    return graph.invoke(state, config=config)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="skip Postgres persistence")
    ap.add_argument("--backend", default="ollama", choices=["ollama", "mlx"])
    ap.add_argument("--date", help="override digest date (YYYY-MM-DD)")
    ap.add_argument("--sample", action="store_true",
                    help="use built-in sample posts instead of live Reddit collection")
    ap.add_argument("--publish", action="store_true",
                    help="write the digest to the blog repo and commit it (stage 8)")
    ap.add_argument("--push", action="store_true",
                    help="with --publish, also push to main (triggers the live Pages deploy)")
    args = ap.parse_args()

    seed = SAMPLE_POSTS if args.sample else None

    day = args.date or datetime.date.today().isoformat()
    digest_key = f"digest-{day}"

    if args.no_db:
        graph = build_graph()
        final = _run(graph, digest_key, run_id=0, seed_posts=seed)
        _print_report(final)
        _maybe_publish(args, digest_key, day, final, use_db=False)
        return

    from langgraph.checkpoint.postgres import PostgresSaver

    db.init_schema()
    run_id = db.create_run(digest_key, trigger="manual")
    with PostgresSaver.from_conn_string(settings.database_url) as cp:
        cp.setup()
        graph = build_graph(checkpointer=cp)
        final = _run(graph, digest_key, run_id=run_id, seed_posts=seed)

    status = final.get("status", "judged")
    db.save_posts(run_id, final.get("posts", []))
    db.save_steps(run_id, final.get("steps", []))
    db.save_digest(run_id, digest_key, final.get("plan"), final.get("draft"),
                   final.get("judge"), status)
    db.finish_run(run_id, status)
    _print_report(final)
    print(f"\n[db] run_id={run_id}  digest_key={digest_key}  status={status}")
    _maybe_publish(args, digest_key, day, final, use_db=True)


if __name__ == "__main__":
    main()
