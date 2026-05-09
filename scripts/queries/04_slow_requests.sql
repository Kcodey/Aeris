-- 查看耗时超过 3 秒的请求
-- 用于定位性能问题

SELECT
    trace_id,
    model,
    latency_ms,
    first_token_ms,
    input_tokens,
    output_tokens,
    timestamp
FROM llm_traces
WHERE latency_ms > 3000
ORDER BY timestamp DESC
LIMIT 20;
