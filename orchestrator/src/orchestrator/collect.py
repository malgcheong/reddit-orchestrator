"""Stage 2: collect. No-auth path via Reddit's public RSS top feed.

Reddit now 403s the `.json` endpoints for non-OAuth clients, but the RSS top
feed still serves without credentials. It is already ranked "top of day", so the
ranking itself is the quality filter. Trade-off: RSS carries no score/comment
counts (left as None). Upgrade path is read-only PRAW (client_id/secret only).

Reddit rate-limits RSS per IP, so we back off on 429 and space subreddit fetches.
A daily run (a few subreddits, once a day) stays well within limits.
"""
import html as html_mod
import re
import time
import xml.etree.ElementTree as ET

import httpx

from .config import settings

ATOM = {"a": "http://www.w3.org/2005/Atom"}
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    s = _TAG_RE.sub(" ", s or "")
    return re.sub(r"\s+", " ", html_mod.unescape(s)).strip()


def _fetch_rss(sub: str, period: str, limit: int, retries: int = 4) -> str:
    # Measured 2026-09: Reddit rate-limits RSS per IP to roughly one request per
    # 45-60s; anything faster 429s. Retry delays must sit above that window.
    url = f"https://www.reddit.com/r/{sub}/top/.rss"
    headers = {"User-Agent": settings.reddit_user_agent}
    params = {"t": period, "limit": limit}
    delay, last = 50.0, None
    for _ in range(retries):
        r = httpx.get(url, params=params, headers=headers, timeout=30)
        if r.status_code == 200 and r.content:
            return r.text
        last = r.status_code
        time.sleep(delay)
        delay *= 1.5
    raise RuntimeError(f"RSS fetch failed for r/{sub}: last status {last}")


def _parse(xml_text: str, sub: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    posts = []
    for e in root.findall("a:entry", ATOM):
        raw_id = e.findtext("a:id", default="", namespaces=ATOM)  # t3_xxxx
        reddit_id = raw_id.split("_", 1)[1] if "_" in raw_id else raw_id
        link_el = e.find("a:link", ATOM)
        posts.append({
            "reddit_id": reddit_id,
            "subreddit": sub,
            "title": e.findtext("a:title", default="", namespaces=ATOM),
            "url": link_el.get("href") if link_el is not None else "",
            "score": None,          # not exposed by RSS
            "num_comments": None,
            "body": _strip_html(e.findtext("a:content", default="", namespaces=ATOM))[:1500],
            "created_utc": e.findtext("a:published", default="", namespaces=ATOM) or None,
        })
    return posts


def collect(subreddits=None, period="day", per_sub=8, pause=55.0) -> list[dict]:
    subs = subreddits or settings.subreddits
    out = []
    for i, sub in enumerate(subs):
        if i:
            time.sleep(pause)  # space requests; RSS rate-limits per IP
        try:
            xml_text = _fetch_rss(sub, period, per_sub * 2)
            out.extend(_parse(xml_text, sub)[:per_sub])
        except Exception as ex:  # one subreddit failing must not kill the run
            print(f"[collect] r/{sub} failed: {ex}")
    return out
