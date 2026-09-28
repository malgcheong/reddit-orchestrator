"""Discord notification for the approval step. Sending only needs a webhook URL
(no bot). With no URL configured it runs in dry mode and prints to the console,
so the approval flow is testable without Discord credentials."""
import httpx

from .config import settings

_ACCENT = 0x2A5DB0


def _preview(draft: str, limit: int = 900) -> str:
    d = (draft or "").strip()
    return d if len(d) <= limit else d[:limit].rstrip() + "\n…"


def _judge_line(judge: dict | None) -> str:
    if not judge:
        return "judge: n/a"
    return (f"정확성 {judge['accuracy']} · 중복 {judge['non_redundancy']} · "
            f"가독성 {judge['readability']} · 확신 {judge['confidence']}")


def _totals(steps: list[dict]) -> str:
    ms = sum(s.get("latency_ms") or 0 for s in steps)
    out = sum(s.get("output_tokens") or 0 for s in steps)
    return f"{ms/1000:.1f}s · {out} tok (로컬, API 비용 0)"


def build_embed(digest_key, plan, judge, draft, steps) -> dict:
    return {
        "embeds": [{
            "title": f"승인 요청 · {plan.get('title', digest_key)}",
            "description": _preview(draft),
            "color": _ACCENT,
            "fields": [
                {"name": "digest", "value": digest_key, "inline": True},
                {"name": "judge", "value": _judge_line(judge), "inline": False},
                {"name": "실행 비용", "value": _totals(steps), "inline": False},
                {"name": "승인/반려", "value":
                    f"`python -m orchestrator.resume {digest_key} approve`\n"
                    f"`python -m orchestrator.resume {digest_key} reject`", "inline": False},
            ],
        }]
    }


def send_approval_request(digest_key, plan, judge, draft, steps) -> bool:
    payload = build_embed(digest_key, plan, judge, draft, steps)
    if not settings.discord_webhook_url:
        e = payload["embeds"][0]
        print("\n" + "─" * 60)
        print(f"[discord dry] {e['title']}")
        for f in e["fields"]:
            print(f"  {f['name']}: {f['value']}")
        print("─" * 60)
        return False
    r = httpx.post(settings.discord_webhook_url, json=payload, timeout=20)
    r.raise_for_status()
    return True


def send_result(digest_key, status, url=None) -> None:
    msg = f"[{digest_key}] {status}" + (f" → {url}" if url else "")
    if not settings.discord_webhook_url:
        print(f"[discord dry] {msg}")
        return
    httpx.post(settings.discord_webhook_url, json={"content": msg}, timeout=20)
