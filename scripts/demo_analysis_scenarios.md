"""
示例数据分析场景 - 用于 Agent 测试

复制以下场景到 Agent 对话中测试数据分析能力:

---
场景 1: Token 使用分析

提问: "分析过去一周的 Token 使用趋势，哪天的用量最高？"

数据库表:
- llm_traces: 包含 trace_id, user_id, provider, model, input_tokens, output_tokens, timestamp
- messages: 包含 conversation_id, role, created_at

---
场景 2: 技能加载成功率

提问: "哪类技能的加载失败率最高？失败原因主要是什么？"

数据库表:
- skill_usages: 包含 skill_name, success, error_message, timestamp

---
场景 3: 模型延迟分布

提问: "帮我分析各模型的延迟分布，找出性能最差的模型"

数据库表:
- llm_traces: 包含 provider, model, latency_ms, first_token_ms

---
场景 4: 决策简报生成

提问: "基于过去7天的数据，生成一个决策简报总结：

1. 主要指标表现（消息量、Token消耗）
2. 异常检测（特别高/低的日期）
3. 建议"

---
场景 5: 用户行为分析

提问: "分析不同用户的消息分布，找出最活跃的用户及其行为特征"

数据库表:
- messages: 包含 user_id, role, created_at
- users: 包含 username, created_at

---
场景 6: 留存分析（测试 cohort analysis 技术）

提问: "按用户注册时间分组，分析新用户的会话参与度变化趋势"

---
场景 7: A/B 测试场景

提问: "比较 anthropic 和 openai 两个 provider 的平均延迟和吞吐量，给出置信区间"

---
场景 8: 异常检测

提问: "检测过去一周是否有异常的数据点（比如 Token 用量突然下降、延迟突然升高）"

---
场景 9: 漏斗分析

提问: "分析用户的会话结构：从创建会话到发送第一条消息的平均时间分布"

---
场景 10: 图表选择建议

提问: "我想要展示每天 Token 消耗的趋势，用什么图表最合适？"

---

直接复制场景编号提问即可测试 Agent 的数据分析能力。
"""