-- 查看所有对话及其 ID
-- 用于找到 conversation_id

SELECT
    id AS conversation_id,
    title,
    status,
    created_at,
    updated_at
FROM conversations
WHERE user_id = 1  -- 替换为你的用户 ID
ORDER BY updated_at DESC;
