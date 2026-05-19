import api from './api'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  collection_name: string
  created_by: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export const ragApi = {
  getKnowledgeBases() {
    return api.get<KnowledgeBase[]>('/rag/kb')
  },
}