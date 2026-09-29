"""Run the orchestration loop on sample or live data.

The loop pauses at the approval step (LangGraph interrupt, checkpointed). Approve
or reject later with `orchestrator.resume`, or pass --auto-approve to decide inline.

  uv run python -m orchestrator.run                 # live collect, pause for approval
  uv run python -m orchestrator.run --sample        # sample posts
  uv run python -m orchestrator.run --auto-approve  # approve inline (test the full loop)
  uv run python -m orchestrator.run --no-db         # in-memory, no persistence
"""
import argparse
import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from . import db, notify
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
    print(f"GATE   : {'PASS' if gate.get('passed') else 'REJECT'}")
    if judge:
        print(f"JUDGE  : acc={judge['accuracy']} nonredun={judge['non_redundancy']} "
              f"read={judge['readability']} conf={judge['confidence']}")
    print("STEPS  :")
    for s in final.get("steps", []):
        model = s.get("model") or "-"
        print(f"         {s['stage']:8s} {s.get('backend') or 'code'}/{model:14s} "
              f"{(s.get('latency_ms') or 0):>6}ms {s['verdict']}")
    print("=" * 60)


def _persist(run_id, final, status):
    db.save_posts(run_id, final.get("posts", []))
    db.save_steps(run_id, final.get("steps", []))
    db.save_digest(run_id, final["digest_key"], final.get("plan"), final.get("draft"),
                   final.get("judge"), status)
    db.finish_run(run_id, status)


def _is_interrupted(result: dict) -> bool:
    return "__interrupt__" in result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="in-memory checkpointer, no persistence")
    ap.add_argument("--sample", action="store_true", help="use built-in sample posts")
    ap.add_argument("--auto-approve", action="store_true", help="approve inline instead of waiting")
    ap.add_argument("--date", help="override digest date (YYYY-MM-DD)")
    args = ap.parse_args()

    day = args.date or datetime.date.today().isoformat()
    digest_key = f"digest-{day}"
    seed = SAMPLE_POSTS if args.sample else None
    config = {"configurable": {"thread_id": digest_key}}
    use_db = not args.no_db

    if use_db:
        db.init_schema()
        run_id = db.create_run(digest_key, trigger="manual")
        from langgraph.checkpoint.postgres import PostgresSaver
        cm = PostgresSaver.from_conn_string(settings.database_url)
    else:
        run_id = 0
        from contextlib import nullcontext
        cm = nullcontext(MemorySaver())

    with cm as cp:
        if use_db:
            cp.setup()
            # A fresh start, not a replay: a leftover checkpoint for this
            # digest_key (an earlier attempt, or a --sample test) would seed old
            # posts and skip live collection. Same-day rerun = replace.
            db.clear_checkpoints(digest_key)
        graph = build_graph(checkpointer=cp)
        state = {"digest_key": digest_key, "run_id": run_id}
        if seed is not None:
            state["posts"] = seed
        result = graph.invoke(state, config=config)

        if _is_interrupted(result):
            _print_report(result)
            if use_db:
                _persist(run_id, result, status="pending_approval")
            notify.send_approval_request(digest_key, result.get("plan"), result.get("judge"),
                                         result.get("draft"), result.get("steps", []))
            if args.auto_approve:
                print("\n[auto-approve] resuming with approved=True")
                result = graph.invoke(Command(resume={"approved": True, "by": "auto"}), config=config)
            else:
                print(f"\n[awaiting approval] resume with: "
                      f"python -m orchestrator.resume {digest_key} approve|reject")
                return

        status = result.get("status", "judged")
        if use_db:
            _persist(run_id, result, status)
            url = (result.get("publish") or {}).get("url")
            if result.get("publish"):
                db.mark_published(digest_key, url or "", status)
        _print_report(result)
        pub = result.get("publish")
        if pub:
            print(f"\n[publish] {pub}")
        print(f"\n[done] digest_key={digest_key} status={status}")


if __name__ == "__main__":
    main()
