import { useEffect, useState } from 'react'
import { message } from 'antd'
import { BookOpen } from 'lucide-react'
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
              className="flex items-center gap-3 p-4 bg-surface-page rounded-lg"
            >
              <div className="w-10 h-10 rounded-lg bg-brand-light flex items-center justify-center">
                <BookOpen size={20} className="text-brand" />
              </div>
              <div>
                <div className="font-medium text-content-primary">{kb.name}</div>
                <div className="text-xs text-content-tertiary">
                  {kb.description || '暂无描述'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}