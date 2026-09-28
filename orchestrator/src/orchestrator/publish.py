"""Stage 8: publish. Write the digest as a Fuwari post and commit it to the blog
repo; pushing to main triggers the GitHub Actions Pages deploy.

Pushing is the one irreversible, outward-facing step, so it is opt-in (`push=True`).
Writing + committing locally is safe and reversible.
"""
import subprocess
from pathlib import Path

from .config import settings


def _yaml_escape(s: str) -> str:
    return (s or "").replace("'", "''")


def _description(body: str, angle: str, limit: int = 150) -> str:
    for para in body.splitlines():
        p = para.strip().lstrip("- ").strip()
        if p and not p.startswith(("#", "*", "[", ":::", "**TL")):
            return p[:limit].strip()
    return (angle or "")[:limit].strip()


def render_post(plan: dict, draft: str, published: str) -> str:
    title = plan.get("title", "레딧 다이제스트")
    desc = _description(draft, plan.get("angle", ""))
    front = (
        "---\n"
        f"title: '{_yaml_escape(title)}'\n"
        f"published: {published}\n"
        f"description: '{_yaml_escape(desc)}'\n"
        "category: '레딧 다이제스트'\n"
        "tags: []\n"
        "draft: false\n"
        "---\n\n"
    )
    return front + (draft or "").strip() + "\n"


def post_path(digest_key: str) -> Path:
    return Path(settings.blog_repo_path) / "src" / "content" / "posts" / f"{digest_key}.md"


def post_url(digest_key: str) -> str:
    return f"{settings.blog_base_url}/posts/{digest_key}/"


def _git(*args) -> str:
    r = subprocess.run(["git", "-C", settings.blog_repo_path, *args],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def publish(digest_key: str, plan: dict, draft: str, published: str, push: bool = False) -> dict:
    path = post_path(digest_key)
    path.write_text(render_post(plan, draft, published), encoding="utf-8")

    rel = f"src/content/posts/{digest_key}.md"
    _git("add", rel)
    staged = subprocess.run(["git", "-C", settings.blog_repo_path, "diff", "--cached", "--quiet"])
    if staged.returncode == 0:
        return {"path": str(path), "committed": False, "pushed": False, "reason": "no change"}

    _git("commit", "-m", f"digest: {plan.get('title', digest_key)} ({digest_key})")
    sha = _git("rev-parse", "--short", "HEAD")
    pushed = False
    if push:
        _git("push", "origin", "main")
        pushed = True
    return {"path": str(path), "committed": True, "pushed": pushed, "sha": sha,
            "url": post_url(digest_key)}
