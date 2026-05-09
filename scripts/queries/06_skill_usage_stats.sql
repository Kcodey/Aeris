-- 查看技能使用统计
-- 展示每个技能的调用次数、成功率、平均延迟

SELECT
    skill_name,
    COUNT(*) AS call_count,
    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) AS success_count,
    ROUND(
        SUM(CASE WHEN success = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
    ) AS success_rate,
    ROUND(AVG(latency_ms), 2) AS avg_latency_ms,
    SUM(latency_ms) AS total_latency_ms,
    MAX(timestamp) AS last_used
FROM skill_usages
WHERE user_id = 1  -- 替换为用户 ID
GROUP BY skill_name
ORDER BY call_count DESC;
