"""LangGraph nodes = the loop stages. Each node returns a step record so every run
leaves an evidence trail (design draft section 9); the `steps` reducer concatenates."""
from langgraph.types import interrupt

from . import publish as pub
from .collect import collect
from .config import settings
from .gateway import Gateway
from .gates import run_gates
from .schemas import DigestPlan, JudgeVerdict

gw = Gateway()


def collect_node(state):
    # Skip live collection if posts were seeded (e.g. --sample or a resumed run).
    if state.get("posts"):
        return {"steps": [_step("collect", verdict="seeded", detail={"count": len(state["posts"])})]}
    posts = collect(settings.subreddits)
    return {
        "posts": posts,
        "steps": [_step("collect", verdict=("ok" if posts else "empty"),
                        detail={"count": len(posts), "subreddits": settings.subreddits})],
    }


def _step(stage, res=None, verdict="ok", detail=None):
    return {
        "stage": stage,
        "model": res.model if res else None,
        "backend": res.backend if res else "code",
        "input_tokens": res.input_tokens if res else None,
        "output_tokens": res.output_tokens if res else None,
        "latency_ms": res.latency_ms if res else None,
        "verdict": verdict,
        "detail": detail or {},
    }


def plan_node(state):
    posts = state["posts"]

    def line(p):
        eng = f" | {p['score']}pts {p.get('num_comments', 0)}c" if p.get("score") is not None else ""
        return f"- id={p['reddit_id']}{eng} | {p['title']}"

    listing = "\n".join(line(p) for p in posts)
    messages = [
        {"role": "system", "content": (
            "You are an editor curating a daily Korean-language AI/dev news digest. Select "
            "exactly 3 to 5 of the most important, non-redundant posts (never fewer than 3 when "
            "that many candidates exist). Write the title and angle in KOREAN. For each pick, put "
            "the exact id value (e.g. s01) in reddit_id. Respond with JSON only per the schema.")},
        {"role": "user", "content": f"Today's candidates:\n{listing}\n\nPick posts and set an editorial angle."},
    ]
    plan, res = gw.generate_json(
        "router", messages, DigestPlan, options={"temperature": 0.2, "num_predict": 800})

    # Backstop: the small router sometimes under-selects. Keep valid, de-duped picks,
    # then top up from the top-ranked candidates (RSS order = top of day), capped at 5.
    ids = [p["reddit_id"] for p in posts]
    known, seen, items = set(ids), set(), []
    for it in plan.include:
        if it.reddit_id in known and it.reddit_id not in seen:
            seen.add(it.reddit_id)
            items.append({"reddit_id": it.reddit_id, "reason": it.reason})
    target = min(3, len(posts))
    for pid in ids:
        if len(items) >= target:
            break
        if pid not in seen:
            seen.add(pid)
            items.append({"reddit_id": pid, "reason": "상위 랭킹 자동 보완"})
    items = items[:5]

    plan_dict = {"title": plan.title, "angle": plan.angle, "include": items}
    return {"plan": plan_dict,
            "steps": [_step("plan", res, detail={"selected": len(items),
                                                 "model_selected": len(plan.include)})]}


def execute_node(state):
    plan = state["plan"]
    by_id = {p["reddit_id"]: p for p in state["posts"]}
    chosen = [by_id[i["reddit_id"]] for i in plan["include"] if i["reddit_id"] in by_id]
    blocks = "\n\n".join(
        f"### {p['title']}\n{p.get('body', '')}\nSource: {p.get('url', '')}" for p in chosen)
    messages = [
        {"role": "system", "content": (
            "You write a concise daily AI/dev digest in Korean Markdown for a Fuwari blog. "
            "Do NOT write an H1 title (the title lives in front-matter). Begin with a TL;DR "
            "admonition exactly in this form:\n"
            ":::note\n**TL;DR**\n- <bullet>\n- <bullet>\n:::\n\n"
            "Then, for each selected item, a `### ` Korean headline, a 2-3 sentence Korean "
            "summary faithful to the source, and the source link as `[원문](URL)` on its own "
            "line. Korean only. Do not invent facts.")},
        {"role": "user", "content": f"Title: {plan['title']}\nAngle: {plan['angle']}\n\nItems:\n{blocks}"},
    ]
    res = gw.generate("worker", messages, options={"temperature": 0.4, "num_predict": 1200})
    return {"draft": res.text, "steps": [_step("execute", res, detail={"chars": len(res.text)})]}


def title_node(state):
    # Title from the (already Korean) draft via the worker, not the router: the
    # small router keeps emitting English titles despite the instruction.
    messages = [
        {"role": "system", "content": (
            "너는 한국어 기술 블로그 편집자다. 아래 다이제스트 본문을 읽고, 오늘 글의 제목을 "
            "한국어로 한 줄만 써라. 25자 안팎, 핵심 주제를 담되 과장·따옴표·마크다운·설명 없이 "
            "제목 텍스트만 출력한다.")},
        {"role": "user", "content": state.get("draft", "")[:2000]},
    ]
    res = gw.generate("worker", messages, options={"temperature": 0.3, "num_predict": 60})
    title = res.text.strip().splitlines()[0].strip().strip("\"'`#·-—").strip()
    plan = dict(state.get("plan") or {})
    fallback = plan.get("title", "레딧 다이제스트")
    plan["title"] = title if title else fallback
    return {"plan": plan, "steps": [_step("title", res, detail={"title": plan["title"]})]}


def gate_node(state):
    gate = run_gates(state.get("plan"), state.get("draft", ""), state["posts"])
    verdict = "pass" if gate["passed"] else "fail"
    return {
        "gate": gate,
        "status": "gated" if gate["passed"] else "rejected",
        "steps": [_step("gate", None, verdict=verdict, detail=gate)],
    }


def judge_node(state):
    messages = [
        {"role": "system", "content": (
            "You are a strict editor. Score the digest draft 1-5 on accuracy, non_redundancy and "
            "readability, give a confidence 0-1 and short notes. Respond with JSON only per the schema.")},
        {"role": "user", "content": state.get("draft", "")},
    ]
    verdict, res = gw.generate_json(
        "worker", messages, JudgeVerdict, options={"temperature": 0.0, "num_predict": 400})
    v = verdict.model_dump()
    return {
        "judge": v,
        "status": "judged",
        "steps": [_step("judge", res, verdict=("pass" if verdict.confidence >= 0.6 else "escalate"), detail=v)],
    }


def approve_node(state):
    # Pause here (checkpointed) until a human resumes with a decision. The resume
    # value is what interrupt() returns; delivered by the Discord bot or resume CLI.
    decision = interrupt({
        "digest_key": state["digest_key"],
        "title": state["plan"].get("title"),
        "judge": state.get("judge"),
    })
    approved = decision.get("approved") if isinstance(decision, dict) else bool(decision)
    by = decision.get("by", "unknown") if isinstance(decision, dict) else "unknown"
    return {
        "approval": {"approved": bool(approved), "by": by},
        "status": "approved" if approved else "rejected",
        "steps": [_step("approve", verdict=("pass" if approved else "fail"), detail={"by": by})],
    }


def publish_node(state):
    if not state.get("approval", {}).get("approved"):
        return {}
    day = state["digest_key"].replace("digest-", "")
    result = pub.publish(state["digest_key"], state["plan"], state["draft"], day,
                         push=settings.blog_auto_push)
    return {
        "publish": result,
        "status": "published" if result.get("pushed") else "approved",
        "steps": [_step("publish", verdict=("pushed" if result.get("pushed") else "committed"),
                        detail=result)],
    }
