package com.malgcheong.orchestra;

import com.malgcheong.orchestra.Models.ModelStat;
import com.malgcheong.orchestra.Models.Overview;
import com.malgcheong.orchestra.Models.RunSummary;
import com.malgcheong.orchestra.Models.StepRow;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class OrchestraRepository {

    private final JdbcTemplate jdbc;

    public OrchestraRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static Double toDouble(java.math.BigDecimal b) {
        return b == null ? null : b.doubleValue();
    }

    public Overview overview() {
        return jdbc.queryForObject("""
                select
                  count(*) as total,
                  count(*) filter (where status = 'published') as published,
                  count(*) filter (where status = 'rejected') as rejected,
                  (select avg(judge_score) from digests) as avg_judge
                from runs
                """,
                (rs, i) -> new Overview(
                        rs.getLong("total"),
                        rs.getLong("published"),
                        rs.getLong("rejected"),
                        toDouble(rs.getBigDecimal("avg_judge"))));
    }

    public List<RunSummary> runs() {
        return jdbc.query("""
                select r.id, r.digest_key, r.status, r.trigger, r.started_at,
                       d.title, d.judge_score, d.published_url,
                       coalesce(sum(s.latency_ms), 0) as total_ms,
                       coalesce(sum(s.output_tokens), 0) as out_tokens
                from runs r
                left join digests d on d.digest_key = r.digest_key
                left join run_steps s on s.run_id = r.id
                group by r.id, d.title, d.judge_score, d.published_url
                order by r.id desc
                """,
                (rs, i) -> new RunSummary(
                        rs.getLong("id"), rs.getString("digest_key"), rs.getString("status"),
                        rs.getString("trigger"),
                        rs.getObject("started_at", java.time.OffsetDateTime.class),
                        rs.getString("title"), toDouble(rs.getBigDecimal("judge_score")),
                        rs.getString("published_url"), rs.getLong("total_ms"),
                        rs.getLong("out_tokens")));
    }

    public List<StepRow> steps(long runId) {
        return jdbc.query("""
                select stage, backend, model, input_tokens, output_tokens, latency_ms, verdict
                from run_steps where run_id = ? order by id
                """,
                (rs, i) -> new StepRow(
                        rs.getString("stage"), rs.getString("backend"), rs.getString("model"),
                        (Integer) rs.getObject("input_tokens"), (Integer) rs.getObject("output_tokens"),
                        (Integer) rs.getObject("latency_ms"), rs.getString("verdict")),
                runId);
    }

    public List<ModelStat> modelStats() {
        return jdbc.query("""
                select model, backend,
                       count(*) as calls,
                       count(*) filter (where verdict in ('ok', 'pass')) as ok,
                       avg(latency_ms) as avg_ms,
                       coalesce(sum(output_tokens), 0) as out_tokens
                from run_steps
                where model is not null
                group by model, backend
                order by calls desc
                """,
                (rs, i) -> new ModelStat(
                        rs.getString("model"), rs.getString("backend"),
                        rs.getLong("calls"), rs.getLong("ok"),
                        rs.getDouble("avg_ms"), rs.getLong("out_tokens")));
    }
}
