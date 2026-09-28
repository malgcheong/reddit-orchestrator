"""Deterministic QA gate (design draft stage 5). Code, not an LLM: plan-nonempty,
ids-exist, no-duplicate-ids, length-range, banned-word checks. Any failure rejects
the run before the judge is asked."""

BANNED = ["lorem ipsum", "todo:", "placeholder", "as an ai language model"]


def run_gates(plan: dict, draft: str, posts: list[dict]) -> dict:
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    include = plan.get("include", []) if plan else []
    planned = [i["reddit_id"] for i in include]
    known_ids = {p["reddit_id"] for p in posts}

    add("plan_nonempty", len(include) >= 1, f"selected={len(include)}")
    unknown = [pid for pid in planned if pid not in known_ids]
    add("ids_exist", not unknown, f"unknown={unknown}")
    add("no_dup_ids", len(planned) == len(set(planned)), f"planned={planned}")

    n = len(draft or "")
    add("length_range", 200 <= n <= 8000, f"chars={n}")

    low = (draft or "").lower()
    hit = [b for b in BANNED if b in low]
    add("no_banned", not hit, f"hits={hit}")

    passed = all(c["ok"] for c in checks)
    return {"passed": passed, "checks": checks}
