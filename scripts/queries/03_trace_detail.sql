-- 查看某次 LLM 调用的完整输入输出
-- 替换 trace_id 即可

SELECT
    trace_id,
    request_payload,
    response_payload,
    latency_ms,
    first_token_ms,
    input_tokens,
    output_tokens,
    timestamp
FROM llm_traces
WHERE trace_id = 'your-trace-id-here';
