import api from './api'

export interface KnowledgeBase {
  id: number
  name: string
  is_active: boolean
  created_at: string
  updated_at: string | null
  document_count: number
  chunk_count: number
}

export const ragApi = {
  getKnowledgeBases() {
    return api.get<KnowledgeBase[]>('/rag/kb')
  },
}