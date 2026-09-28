"""LangGraph nodes = the loop stages. Each node returns a step record so every run
leaves an evidence trail (design draft section 9); the `steps` reducer concatenates."""
from .gateway import Gateway
from .gates import run_gates
from .schemas import DigestPlan, JudgeVerdict

gw = Gateway()


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
    listing = "\n".join(
        f"- id={p['reddit_id']} | {p['score']}pts {p['num_comments']}c | {p['title']}"
        for p in posts
    )
    messages = [
        {"role": "system", "content": (
            "You are an editor curating a daily Korean-language AI/dev news digest. From the "
            "candidates, select the 3-5 most important, non-redundant posts. For each pick, put "
            "the exact id value (e.g. s01) in reddit_id. Respond with JSON only per the schema.")},
        {"role": "user", "content": f"Today's candidates:\n{listing}\n\nPick posts and set an editorial angle."},
    ]
    plan, res = gw.generate_json(
        "router", messages, DigestPlan, options={"temperature": 0.2, "num_predict": 800})
    return {"plan": plan.model_dump(), "steps": [_step("plan", res, detail={"selected": len(plan.include)})]}


def execute_node(state):
    plan = state["plan"]
    by_id = {p["reddit_id"]: p for p in state["posts"]}
    chosen = [by_id[i["reddit_id"]] for i in plan["include"] if i["reddit_id"] in by_id]
    blocks = "\n\n".join(
        f"### {p['title']}\n{p.get('body', '')}\nSource: {p.get('url', '')}" for p in chosen)
    messages = [
        {"role": "system", "content": (
            "You write a concise daily AI/dev digest in Korean Markdown. Start with an H1 title "
            "and a one-line intro reflecting the angle. For each item: a bold Korean headline, a "
            "2-3 sentence Korean summary faithful to the source, then the source link on its own "
            "line. Do not invent facts.")},
        {"role": "user", "content": f"Title: {plan['title']}\nAngle: {plan['angle']}\n\nItems:\n{blocks}"},
    ]
    res = gw.generate("worker", messages, options={"temperature": 0.4, "num_predict": 1200})
    return {"draft": res.text, "steps": [_step("execute", res, detail={"chars": len(res.text)})]}


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
