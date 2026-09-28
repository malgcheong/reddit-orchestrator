#!/usr/bin/env python3
"""Measure real generation + prefill speed of the local Ollama models on this box.

Fills in the design draft's estimated speed table (docs) with measured numbers.
Stdlib only, so it runs on the system Python without a venv.
"""
import json
import time
import urllib.request

OLLAMA = "http://localhost:11434/api/generate"
MODELS = ["lfm2.5:8b", "qwen3.5:9b", "qwen3.5:4b"]

# ~ a few thousand tokens of filler to exercise prefill.
LONG_CONTEXT = ("The following is a long English technology article about "
                "large language models, inference, and Apple Silicon. ") * 250


def call(model: str, prompt: str, num_predict: int) -> dict:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": num_predict},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def rate(count, duration_ns):
    if not count or not duration_ns:
        return 0.0
    return count / (duration_ns / 1e9)


def main():
    rows = []
    for m in MODELS:
        print(f"\n=== {m} ===", flush=True)
        # warm-up / load
        call(m, "hi", 1)
        # generation speed: force a decent number of output tokens
        gen = call(m, "Write a 200-word summary of how transformers work.", 220)
        gen_tps = rate(gen.get("eval_count"), gen.get("eval_duration"))
        # prefill speed: large prompt, single output token
        pf = call(m, LONG_CONTEXT + "\n\nSummarize in one sentence.", 1)
        pf_tps = rate(pf.get("prompt_eval_count"), pf.get("prompt_eval_duration"))
        print(f"  generate: {gen_tps:5.1f} tok/s  (eval_count={gen.get('eval_count')})")
        print(f"  prefill : {pf_tps:6.1f} tok/s  (prompt_eval_count={pf.get('prompt_eval_count')})")
        rows.append((m, gen_tps, pf_tps, pf.get("prompt_eval_count")))

    print("\n\n## Measured on this machine\n")
    print("| model | generate (tok/s) | prefill (tok/s) |")
    print("|---|---|---|")
    for m, g, p, _ in rows:
        print(f"| {m} | {g:.1f} | {p:.0f} |")


if __name__ == "__main__":
    main()
