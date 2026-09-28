"""Deliver an approve/reject decision to a run paused at the approval step.

Used by the resume CLI and by the Discord bot. Resuming a checkpointed graph with
the decision continues from the approval node into publish (on approve) or END.

  uv run python -m orchestrator.resume digest-2026-09-28 approve
  uv run python -m orchestrator.resume digest-2026-09-28 reject
"""
import argparse

from langgraph.types import Command

from . import db, notify
from .config import settings
from .graph import build_graph


def apply_decision(digest_key: str, approved: bool, by: str = "malgcheong") -> dict:
    config = {"configurable": {"thread_id": digest_key}}
    from langgraph.checkpoint.postgres import PostgresSaver
    with PostgresSaver.from_conn_string(settings.database_url) as cp:
        cp.setup()
        graph = build_graph(checkpointer=cp)
        result = graph.invoke(Command(resume={"approved": approved, "by": by}), config=config)

    status = result.get("status", "rejected")
    run_id = db.get_run_id(digest_key)
    if run_id:
        db.save_steps(run_id, result.get("steps", []))
        db.save_digest(run_id, digest_key, result.get("plan"), result.get("draft"),
                       result.get("judge"), status)
        db.finish_run(run_id, status)
        if result.get("publish"):
            db.mark_published(digest_key, result["publish"].get("url", ""), status)

    url = (result.get("publish") or {}).get("url")
    notify.send_result(digest_key, status, url)
    return {"status": status, "publish": result.get("publish")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("digest_key")
    ap.add_argument("decision", choices=["approve", "reject"])
    ap.add_argument("--by", default="malgcheong")
    args = ap.parse_args()

    out = apply_decision(args.digest_key, args.decision == "approve", args.by)
    print(f"[resume] {args.digest_key} -> {out['status']}")
    if out.get("publish"):
        print(f"[publish] {out['publish']}")


if __name__ == "__main__":
    main()
