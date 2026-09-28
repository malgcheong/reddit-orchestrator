package com.malgcheong.orchestra;

import java.time.OffsetDateTime;

/** Read-only view records over the shared orchestrator schema. */
public final class Models {
    private Models() {}

    public record Overview(long totalRuns, long published, long rejected, Double avgJudge) {}

    public record RunSummary(
            long id, String digestKey, String status, String trigger,
            OffsetDateTime startedAt, String title, Double judgeScore,
            String publishedUrl, long totalMs, long outTokens) {}

    public record StepRow(
            String stage, String backend, String model,
            Integer inputTokens, Integer outputTokens, Integer latencyMs, String verdict) {}

    public record ModelStat(
            String model, String backend, long calls, long ok,
            double avgMs, long outTokens) {
        public long okRatePct() { return calls == 0 ? 0 : Math.round(100.0 * ok / calls); }
    }
}
