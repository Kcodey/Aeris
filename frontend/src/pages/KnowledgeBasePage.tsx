import { useEffect, useState } from 'react'
import { message } from 'antd'
import { BookOpen, FileText, Clock } from 'lucide-react'
import { ragApi, KnowledgeBase } from '../services/rag'

export default function KnowledgeBasePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  const loadKnowledgeBases = async () => {
    try {
      setLoading(true)
      const response = await ragApi.getKnowledgeBases()
      setKnowledgeBases(response.data)
    } catch (error) {
      console.error('Failed to load knowledge bases:', error)
      message.error('加载知识库失败')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string | null, fallback: string | null) => {
    if (dateStr) return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    if (fallback) return new Date(fallback).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    return '-'
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl p-6">
      <div className="flex items-center gap-2 mb-6">
        <BookOpen size={20} className="text-brand" />
        <h1 className="text-lg font-semibold text-content-primary">我的知识库</h1>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-content-tertiary">加载中...</span>
        </div>
      ) : knowledgeBases.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-content-tertiary">
          <BookOpen size={48} className="opacity-20 mb-3" />
          <p>暂无知识库</p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto space-y-3">
          {knowledgeBases.map(kb => (
            <div
              key={kb.id}
              className="flex items-center gap-4 p-4 bg-surface-page rounded-lg hover:bg-[#F5F5F5] transition-colors"
            >
              <div className="w-12 h-12 rounded-lg bg-brand-light flex items-center justify-center shrink-0">
                <BookOpen size={24} className="text-brand" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-content-primary text-base">{kb.name}</div>
                <div className="text-sm text-content-secondary mt-1">
                  {kb.description || '暂无描述'}
                </div>
                <div className="flex items-center gap-4 mt-2 text-xs text-content-tertiary">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {formatDate(kb.updated_at, kb.created_at)}
                  </span>
                  <span className="flex items-center gap-1">
                    <FileText size={12} />
                    {kb.collection_name}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}