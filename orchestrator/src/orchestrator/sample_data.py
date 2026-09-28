"""Sample candidates for dry-runs, so stages 3-6 (plan/execute/gate/judge) can run
without Reddit credentials. Replaced by the real collector (stage 2) later."""

SAMPLE_POSTS = [
    {
        "reddit_id": "s01", "subreddit": "LocalLLaMA",
        "title": "Qwen3.5 released: 4B / 9B / 35B with 256K context",
        "url": "https://reddit.com/r/LocalLLaMA/s01", "score": 1240, "num_comments": 312,
        "body": ("Alibaba released the Qwen3.5 family in 4B, 9B and 35B sizes, all with a "
                 "256K context window and improved tool-calling. Community MLX and GGUF "
                 "quants appeared within hours."),
    },
    {
        "reddit_id": "s02", "subreddit": "LocalLLaMA",
        "title": "Running a 9B model at 18 tok/s on a base M4 Mac mini (16GB)",
        "url": "https://reddit.com/r/LocalLLaMA/s02", "score": 690, "num_comments": 154,
        "body": ("A user benchmarked several local models on a 16GB M4 Mac mini and found "
                 "dense 9B models generate around 18 tokens/sec, while small MoE routers hit "
                 "70+ tokens/sec thanks to the low active parameter count."),
    },
    {
        "reddit_id": "s03", "subreddit": "MachineLearning",
        "title": "Constrained decoding cuts tool-call JSON errors to near zero",
        "url": "https://reddit.com/r/MachineLearning/s03", "score": 430, "num_comments": 88,
        "body": ("A paper shows that grammar-constrained decoding (JSON schema to grammar) "
                 "reduces malformed structured outputs from ~20% to under 1% for 7-14B models, "
                 "without hurting task quality."),
    },
    {
        "reddit_id": "s04", "subreddit": "LocalLLaMA",
        "title": "LFM2.5-8B-A1B: a MoE that actually fits in 16GB",
        "url": "https://reddit.com/r/LocalLLaMA/s04", "score": 512, "num_comments": 97,
        "body": ("Liquid released LFM2.5-8B-A1B, a mixture-of-experts model with ~1.5B active "
                 "parameters. Because only the active experts are read per token, it runs fast "
                 "on memory-bandwidth-limited machines while fitting comfortably in 16GB."),
    },
    {
        "reddit_id": "s05", "subreddit": "programming",
        "title": "Show: an autonomous agent loop with a deterministic QA gate",
        "url": "https://reddit.com/r/programming/s05", "score": 275, "num_comments": 61,
        "body": ("A developer wired an LLM agent loop where a deterministic code gate (link "
                 "checks, dedup, length, schema) runs before an LLM judge, with Discord "
                 "approval and automatic rollback on post-publish failures."),
    },
]
