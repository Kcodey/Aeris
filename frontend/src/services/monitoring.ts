import api from './api'
import { DashboardStats, ModelUsage, LLMTrace } from '../types/monitoring'

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
}
