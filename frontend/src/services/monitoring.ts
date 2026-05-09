import api from './api'
import { DashboardStats, ModelUsage, LLMTrace, SkillUsageStat, SkillUsageTimeline, SkillUsageRecord } from '../types/monitoring'

export const monitoringApi = {
  getDashboard: (hours?: number) =>
    api.get<DashboardStats>('/monitoring/dashboard', { params: { hours } }),

  getModelUsage: (hours?: number) =>
    api.get<ModelUsage[]>('/monitoring/model-usage', { params: { hours } }),

  getTraces: (params?: { skip?: number; limit?: number; conversation_id?: number }) =>
    api.get<LLMTrace[]>('/monitoring/traces', { params }),

  getTraceDetail: (traceId: string) =>
    api.get<LLMTrace>(`/monitoring/traces/${traceId}`),

  getDailyStats: (hours?: number) =>
    api.get<{ period_hours: number; daily_tokens: { date: string; tokens: number }[]; latency_distribution: { range: string; count: number }[] }>('/monitoring/daily-stats', { params: { hours } }),

  // Skill usage APIs
  getSkillUsageStats: (hours?: number) =>
    api.get<{ period_hours: number; stats: SkillUsageStat[]; total_calls: number }>('/monitoring/skill-usage/stats', { params: { hours } }),

  getSkillUsageTimeline: (skillName?: string, hours?: number) =>
    api.get<SkillUsageTimeline>('/monitoring/skill-usage/timeline', { params: { skill_name: skillName, hours } }),

  getRecentSkillUsage: (limit?: number) =>
    api.get<SkillUsageRecord[]>('/monitoring/skill-usage/recent', { params: { limit } }),
}
