export interface DashboardStats {
  period_days: number
  total_messages: number
  total_conversations: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  avg_latency_ms: number
}

export interface ModelUsage {
  provider: string
  model: string
  count: number
  input_tokens: number
  output_tokens: number
  avg_first_token_ms: number
  avg_tokens_per_second: number
}

export interface LLMTrace {
  trace_id: string
  user_id: number
  conversation_id: number
  message_id?: number
  provider: string
  model: string
  timestamp: string
  latency_ms: number
  first_token_ms?: number
  tokens_per_second?: number
  input_tokens: number
  output_tokens: number
  tokens_estimated?: boolean
  request_payload?: Record<string, any>
  response_payload?: Record<string, any>
  tool_calls?: any[]
  tool_results?: any[]
  iteration_count?: number
  error_type?: string
  error_message?: string
}

export interface SkillUsageStat {
  skill_name: string
  call_count: number
  success_count: number
  success_rate: number
  avg_latency_ms: number
  total_latency_ms: number
}

export interface SkillUsageTimeline {
  skill_name?: string
  period_hours: number
  timeline: { hour: string; count: number }[]
}

export interface SkillUsageRecord {
  id: number
  skill_name: string
  success: boolean
  latency_ms: number
  timestamp: string
  conversation_id: number
}
