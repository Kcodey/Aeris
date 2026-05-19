import { useEffect, useState } from 'react'
import { Switch, message } from 'antd'
import { Modal } from 'antd'
import { BookOpen } from 'lucide-react'
import { ragApi, KnowledgeBase } from '../services/rag'
import { chatApi } from '../services/chat'
import { Conversation } from '../types/chat'

interface KnowledgeBasePageProps {
  conversations?: Conversation[]
  selectedConversationId?: number | null
  onRefreshConversations?: () => void
}

export default function KnowledgeBasePage({
  conversations = [],
  selectedConversationId = null,
  onRefreshConversations,
}: KnowledgeBasePageProps) {
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

  // 获取当前对话的 KB ids
  const getCurrentKBIds = (): number[] => {
    if (!selectedConversationId) return []
    const conv = conversations.find(c => c.id === selectedConversationId)
    return conv?.knowledge_base_ids || []
  }

  // 判断某个 KB 是否启用
  const isKBEnabled = (kbId: number): boolean => {
    return getCurrentKBIds().includes(kbId)
  }

  // 处理 Toggle 切换
  const handleToggle = async (kb: KnowledgeBase, enabled: boolean) => {
    if (!selectedConversationId) {
      message.warning('请先选择一个对话')
      return
    }

    const currentIds = getCurrentKBIds()
    let newIds: number[]
    if (enabled) {
      newIds = [...currentIds, kb.id]
    } else {
      newIds = currentIds.filter(id => id !== kb.id)
    }

    try {
      await chatApi.updateConversation(selectedConversationId, {
        knowledge_base_ids: newIds
      })
      message.success(enabled ? `已启用${kb.name}` : `已禁用${kb.name}`)
      onRefreshConversations?.()
    } catch (error) {
      console.error('Failed to update conversation:', error)
      message.error('操作失败，请重试')
    }
  }

  // 确认框
  const showConfirm = (kb: KnowledgeBase, enabled: boolean) => {
    if (!selectedConversationId) {
      message.warning('请先选择一个对话')
      return
    }

    Modal.confirm({
      title: enabled ? '启用知识库' : '禁用知识库',
      content: `${enabled ? '启用' : '禁用'}后将${enabled ? '为此对话启用' : '关闭'}「${kb.name}」检索`,
      okText: enabled ? '启用' : '禁用',
      cancelText: '取消',
      onOk: () => handleToggle(kb, enabled),
    })
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
              className="flex items-center justify-between p-4 bg-surface-page rounded-lg hover:bg-[#F5F5F5] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-light flex items-center justify-center">
                  <BookOpen size={20} className="text-brand" />
                </div>
                <div>
                  <div className="font-medium text-content-primary">{kb.name}</div>
                  <div className="text-xs text-content-tertiary">
                    最后更新: {kb.updated_at ? new Date(kb.updated_at).toLocaleDateString('zh-CN') : '-'}
                  </div>
                </div>
              </div>
              <Switch
                checked={isKBEnabled(kb.id)}
                onChange={(checked) => showConfirm(kb, checked)}
                disabled={!selectedConversationId}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}