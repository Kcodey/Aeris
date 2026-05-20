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

export interface Document {
  id: number
  knowledge_base_id: number
  title: string
  source_type: string
  source_path: string
  status: string
  chunk_count: number
  created_at: string
  updated_at: string | null
}

export interface KnowledgeBaseDetail {
  id: number
  name: string
  is_active: boolean
  created_at: string
  updated_at: string | null
  document_count: number
  chunk_count: number
  documents: Document[]
}

export const ragApi = {
  getKnowledgeBases() {
    return api.get<KnowledgeBase[]>('/rag/kb')
  },
  getKnowledgeBaseDetail(kbId: number) {
    return api.get<KnowledgeBaseDetail>(`/rag/kb/${kbId}`)
  },
}