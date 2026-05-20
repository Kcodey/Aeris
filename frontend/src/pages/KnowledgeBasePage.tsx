import { useEffect, useState } from 'react'
import { message } from 'antd'
import { BookOpen, FileText, Layers } from 'lucide-react'
import { ragApi, KnowledgeBase } from '../services/rag'
import { KBDetailDrawer } from '../components/KnowledgeBase/KBDetailDrawer'

export default function KnowledgeBasePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedKbId, setSelectedKbId] = useState<number | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

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

  const handleKbClick = (kbId: number) => {
    setSelectedKbId(kbId)
    setDrawerOpen(true)
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
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
            {knowledgeBases.map(kb => (
              <div
                key={kb.id}
                onClick={() => handleKbClick(kb.id)}
                className="group relative flex flex-col rounded-2xl p-5 bg-gradient-to-br from-[#FFFBF5] to-[#FFF8F0] hover:from-[#FFFDF8] hover:to-[#FFF5E6] border border-[#F5E6D3] hover:border-[#E8D5C4] hover:shadow-lg transition-all duration-300 cursor-pointer overflow-hidden"
                style={{ aspectRatio: '3/4' }}
              >
                {/* 顶部装饰 */}
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[#FFE4B5]/30 to-transparent rounded-bl-full" />

                {/* 图标 */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand/10 to-amber-100 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                  <BookOpen size={22} className="text-brand" />
                </div>

                {/* 标题 */}
                <div className="flex-1">
                  <h3 className="font-medium text-[#3D2C1E] text-[15px] leading-snug mb-2 line-clamp-2">
                    {kb.name}
                  </h3>
                  <p className="text-xs text-[#A08060]">
                    更新于 {formatDate(kb.updated_at, kb.created_at)}
                  </p>
                </div>

                {/* 底部统计 */}
                <div className="flex items-center gap-4 pt-3 border-t border-[#F0E0D0]/50 mt-3">
                  <div className="flex items-center gap-1.5 text-xs text-[#7A6550]">
                    <FileText size={13} />
                    <span>{kb.document_count}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-[#7A6550]">
                    <Layers size={13} />
                    <span>{kb.chunk_count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <KBDetailDrawer
        kbId={selectedKbId}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}