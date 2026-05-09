-- 查看最近 10 次 LLM 调用
-- 用于排查模型响应慢、返回空等问题

SELECT
    trace_id,
    model,
    latency_ms,
    first_token_ms,
    input_tokens,
    output_tokens,
    error_type,
    timestamp
FROM llm_traces
ORDER BY timestamp DESC
LIMIT 10;
