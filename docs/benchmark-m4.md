# Local model benchmark — Mac mini M4 (16GB)

Machine: Apple M4 (Mac16,10), 10-core CPU (4P+6E), 10-core GPU, 16GB unified memory (~120 GB/s), macOS 26.2.
Backend: Ollama 0.34.4 (llama.cpp / GGUF path). Measured with `scripts/benchmark.py`
(`/api/generate`, 2K-token prompt, temperature 0, 220 output tokens).

| model | role | generate (tok/s) | prefill (tok/s) |
|---|---|---|---|
| lfm2.5:8b | router / planner / extractor (MoE, ~1.5B active) | 78.8 | 825 |
| qwen3.5:4b | light worker (parallel / classify) | 28.0 | 382 |
| qwen3.5:9b | quality worker (summary / draft / judge) | 18.1 | 204 |

Notes:
- These beat the M1 estimates in the original design draft by ~1.5-2.3x, as expected
  from the bandwidth jump (M1 68 GB/s -> M4 ~120 GB/s) and 10-core GPU.
- Memory budget is unchanged from the draft (16GB is 16GB): keep model + KV cache
  <= ~11-12GB, `OLLAMA_MAX_LOADED_MODELS=2`, router always resident.
- Ollama runs the GGUF path (its experimental MLX backend needs 32GB). Standalone
  `mlx-lm` runs fine on this 16GB M4 and will be benchmarked head-to-head against
  the GGUF numbers above (that comparison is a portfolio deliverable).
