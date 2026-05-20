import { useEffect, useState } from 'react'
import { Drawer, Spin, message } from 'antd'
import { BookOpen, FileText, Layers, Link, Upload, RefreshCw, AlertCircle } from 'lucide-react'
import { ragApi, KnowledgeBaseDetail, Document } from '../../services/rag'

interface KBDetailDrawerProps {
  kbId: number | null
  open: boolean
  onClose: () => void
}

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'ready':
      return { color: '#52c41a', label: '就绪', icon: <FileText size={12} /> }
    case 'processing':
      return { color: '#1890ff', label: '处理中', icon: <RefreshCw size={12} className="animate-spin" /> }
    case 'failed':
      return { color: '#ff4d4f', label: '失败', icon: <AlertCircle size={12} /> }
    default:
      return { color: '#999', label: status, icon: <FileText size={12} /> }
  }
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

export const KBDetailDrawer: React.FC<KBDetailDrawerProps> = ({ kbId, open, onClose }) => {
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<KnowledgeBaseDetail | null>(null)

  useEffect(() => {
    if (kbId && open) {
      loadDetail()
    }
  }, [kbId, open])

  const loadDetail = async () => {
    if (!kbId) return
    try {
      setLoading(true)
      const response = await ragApi.getKnowledgeBaseDetail(kbId)
      setDetail(response.data)
    } catch (error) {
      console.error('Failed to load KB detail:', error)
      message.error('加载知识库详情失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Drawer
      title={
        <div className="flex items-center gap-2">
          <BookOpen size={18} className="text-brand" />
          <span className="font-medium">{detail?.name || '知识库详情'}</span>
        </div>
      }
      placement="right"
      onClose={onClose}
      open={open}
      width={520}
      styles={{ body: { padding: 0 } }}
    >
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Spin />
        </div>
      ) : detail ? (
        <div className="flex flex-col h-full">
          {/* 统计卡片 */}
          <div className="p-5 bg-gradient-to-r from-[#FFFBF5] to-[#FFF8F0] border-b border-[#F0E0D0]">
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-lg bg-white shadow-sm flex items-center justify-center">
                  <FileText size={16} className="text-brand" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-[#3D2C1E]">{detail.document_count}</div>
                  <div className="text-xs text-[#A08060]">文档</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-lg bg-white shadow-sm flex items-center justify-center">
                  <Layers size={16} className="text-brand" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-[#3D2C1E]">{detail.chunk_count}</div>
                  <div className="text-xs text-[#A08060]">Chunks</div>
                </div>
              </div>
              <div className="ml-auto text-xs text-[#A08060]">
                更新于 {formatDate(detail.updated_at || detail.created_at)}
              </div>
            </div>
          </div>

          {/* 文档列表 */}
          <div className="flex-1 overflow-auto p-4">
            {detail.documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-[#A08060]">
                <FileText size={40} className="opacity-20 mb-2" />
                <p>暂无文档</p>
              </div>
            ) : (
              <div className="space-y-3">
                {detail.documents.map(doc => {
                  const statusConfig = getStatusConfig(doc.status)
                  const isUrl = doc.source_type === 'url'

                  return (
                    <div
                      key={doc.id}
                      className="bg-white rounded-xl p-4 border border-[#F0E0D0] hover:border-[#E8D5C4] hover:shadow-sm transition-all"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                          isUrl ? 'bg-blue-50' : 'bg-amber-50'
                        }`}>
                          {isUrl ? <Link size={18} className="text-blue-500" /> : <Upload size={18} className="text-amber-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-[#3D2C1E] text-sm truncate flex-1">
                              {doc.title}
                            </h4>
                            <span
                              className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full"
                              style={{ backgroundColor: `${statusConfig.color}15`, color: statusConfig.color }}
                            >
                              {statusConfig.icon}
                              {statusConfig.label}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 mt-1.5 text-xs text-[#A08060]">
                            <span className="flex items-center gap-1">
                              <Layers size={11} />
                              {doc.chunk_count} chunks
                            </span>
                            <span>{formatDate(doc.updated_at || doc.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Drawer>
  )
}