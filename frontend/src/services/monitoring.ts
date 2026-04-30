import api from './api'
import { DashboardStats, ModelUsage, LLMTrace } from '../types/monitoring'

export const monitoringApi = {
  getDashboard: (days?: number) =>
    api.get<DashboardStats>('/monitoring/dashboard', { params: { days } }),

  getModelUsage: (days?: number) =>
    api.get<ModelUsage[]>('/monitoring/model-usage', { params: { days } }),

  getTraces: (params?: { skip?: number; limit?: number }) =>
    api.get<LLMTrace[]>('/monitoring/traces', { params }),

  getTraceDetail: (traceId: string) =>
    api.get<LLMTrace>(`/monitoring/traces/${traceId}`),
}
