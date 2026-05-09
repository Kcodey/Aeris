-- 查看某个对话的完整消息历史
-- 替换 conversation_id 即可

SELECT
    id,
    role,
    LEFT(content, 200) AS content_preview,
    input_tokens,
    output_tokens,
    created_at
FROM messages
WHERE conversation_id = 27
ORDER BY created_at;
