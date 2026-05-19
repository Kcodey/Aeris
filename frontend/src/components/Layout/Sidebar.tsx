import React from 'react'
import { MessageSquare, BarChart3, LogOut, Plus, X, Edit2, Check, Trash2, Info, BookOpen } from 'lucide-react'
import { Conversation } from '../../types/chat'
import { ConversationDetailDrawer } from '../Chat/ConversationDetailDrawer'

interface SidebarProps {
  activeRoute: string
  conversations: Conversation[]
  selectedConversationId: number | null
  onNavigate: (route: string) => void
  onSelectConversation: (id: number) => void
  onCreateConversation: () => void
  onLogout: () => void
  onUpdateTitle?: (id: number, title: string) => void
  onDeleteConversation?: (id: number) => void
  mobileOpen?: boolean
  onMobileClose?: () => void
}

// 时间分组工具函数
function getTimeGroup(dateStr: string | null): string {
  if (!dateStr) return '更早'

  const date = new Date(dateStr)
  // 转换为北京时间 (UTC+8)
  const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const now = new Date()
  const beijingNow = new Date(now.getTime() + 8 * 60 * 60 * 1000)

  const today = new Date(beijingNow.getFullYear(), beijingNow.getMonth(), beijingNow.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const thisWeekStart = new Date(today)
  thisWeekStart.setDate(thisWeekStart.getDate() - thisWeekStart.getDay())

  const dateOnly = new Date(beijingDate.getFullYear(), beijingDate.getMonth(), beijingDate.getDate())

  if (dateOnly.getTime() === today.getTime()) {
    return '今天'
  } else if (dateOnly.getTime() === yesterday.getTime()) {
    return '昨天'
  } else if (dateOnly >= thisWeekStart) {
    return '本周'
  } else {
    return '更早'
  }
}

// 格式化时间显示
function formatTime(dateStr: string | null): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  // 转换为北京时间 (UTC+8)
  const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const now = new Date()
  const beijingNow = new Date(now.getTime() + 8 * 60 * 60 * 1000)

  const today = new Date(beijingNow.getFullYear(), beijingNow.getMonth(), beijingNow.getDate())
  const dateOnly = new Date(beijingDate.getFullYear(), beijingDate.getMonth(), beijingDate.getDate())

  const hours = beijingDate.getHours().toString().padStart(2, '0')
  const minutes = beijingDate.getMinutes().toString().padStart(2, '0')

  if (dateOnly.getTime() === today.getTime()) {
    return `${hours}:${minutes}`
  } else {
    const month = (beijingDate.getMonth() + 1).toString()
    const day = beijingDate.getDate().toString()
    return `${month}月${day}日`
  }
}

// 编辑标题组件
const EditableTitle: React.FC<{
  title: string | null
  isEditing: boolean
  onStartEdit: () => void
  onSave: (title: string) => void
  onCancel: () => void
  onDelete?: () => void
  onDetail?: () => void
}> = ({ title, isEditing, onStartEdit, onSave, onCancel, onDelete, onDetail }) => {
  const [editValue, setEditValue] = React.useState(title || '')

  React.useEffect(() => {
    setEditValue(title || '')
  }, [title, isEditing])

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 flex-1">
        <input
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              onSave(editValue)
            } else if (e.key === 'Escape') {
              onCancel()
            }
          }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 px-1 py-0.5 text-xs bg-white border border-brand rounded focus:outline-none focus:ring-1 focus:ring-brand"
          autoFocus
        />
        <button
          onClick={(e) => {
            e.stopPropagation()
            onSave(editValue)
          }}
          className="p-0.5 text-brand hover:bg-brand/10 rounded"
        >
          <Check size={12} />
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1 flex-1 min-w-0">
      <span className="truncate flex-1">
        {title || '新对话'}
      </span>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onStartEdit()
        }}
        className="opacity-0 group-hover:opacity-100 p-0.5 text-content-tertiary hover:text-content-secondary hover:bg-surface-page rounded transition-all"
      >
        <Edit2 size={12} />
      </button>
      {onDetail && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDetail()
          }}
          className="opacity-0 group-hover:opacity-100 p-0.5 text-content-tertiary hover:text-brand hover:bg-brand/10 rounded transition-all"
          title="查看详情"
        >
          <Info size={12} />
        </button>
      )}
      {onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          className="opacity-0 group-hover:opacity-100 p-0.5 text-content-tertiary hover:text-red-500 hover:bg-red-50 rounded transition-all"
          title="删除对话"
        >
          <Trash2 size={12} />
        </button>
      )}
    </div>
  )
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeRoute,
  conversations,
  selectedConversationId,
  onNavigate,
  onSelectConversation,
  onCreateConversation,
  onLogout,
  onUpdateTitle,
  onDeleteConversation,
  mobileOpen = false,
  onMobileClose,
}) => {
  const [editingId, setEditingId] = React.useState<number | null>(null)
  const [detailConversation, setDetailConversation] = React.useState<Conversation | null>(null)
  const [detailOpen, setDetailOpen] = React.useState(false)

  const navItems = [
    { key: '/', label: '对话', icon: MessageSquare },
    { key: '/kb', label: '知识库', icon: BookOpen },
    { key: '/monitoring', label: '监控', icon: BarChart3 },
  ]

  const handleNav = (route: string) => {
    onNavigate(route)
    onMobileClose?.()
  }

  const handleSelect = (id: number) => {
    onSelectConversation(id)
    onMobileClose?.()
  }

  const handleSaveTitle = (id: number, title: string) => {
    onUpdateTitle?.(id, title)
    setEditingId(null)
  }

  // 按时间分组对话
  const groupedConversations = React.useMemo(() => {
    const groups: Record<string, Conversation[]> = {
      '今天': [],
      '昨天': [],
      '本周': [],
      '更早': [],
    }

    conversations.forEach((conv) => {
      const group = getTimeGroup(conv.updated_at)
      groups[group].push(conv)
    })

    // 只返回非空分组
    return Object.entries(groups).filter(([, items]) => items.length > 0)
  }, [conversations])

  const sidebarContent = (
    <>
      {/* Brand */}
      <div className="px-2 mb-4 flex items-center justify-between">
        <span className="text-sm font-bold text-brand">Meditatio</span>
        <div className="flex items-center gap-1">
          <button
            onClick={onCreateConversation}
            className="w-7 h-7 rounded-lg bg-brand-light flex items-center justify-center text-brand hover:bg-brand/10 transition-colors"
            title="新建对话"
          >
            <Plus size={16} />
          </button>
          {mobileOpen && onMobileClose && (
            <button
              onClick={onMobileClose}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-content-secondary hover:bg-surface-page transition-colors md:hidden"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 mb-3">
        {navItems.map((item) => {
          const isActive = activeRoute === item.key
          const Icon = item.icon
          return (
            <button
              key={item.key}
              onClick={() => handleNav(item.key)}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-md text-xs font-medium transition-all duration-150 relative ${
                isActive
                  ? 'bg-white text-content-primary font-semibold shadow-[0_2px_8px_rgba(0,0,0,0.08)] -translate-y-0.5'
                  : 'text-content-secondary hover:bg-[#EFEFEF]'
              }`}
            >
              <Icon size={16} />
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* Divider */}
      <div className="border-t border-border mx-2 my-2" />

      {/* Conversation List */}
      <div className="flex-1 overflow-auto -mx-1 px-1">
        {conversations.length === 0 ? (
          <button
            onClick={onCreateConversation}
            className="w-full text-center py-8 text-content-tertiary hover:text-content-secondary hover:bg-surface-page rounded-lg transition-colors"
          >
            <MessageSquare size={32} className="mx-auto mb-2 opacity-30" />
            <p className="text-xs">开始一个新对话</p>
          </button>
        ) : (
          <div className="flex flex-col gap-3">
            {groupedConversations.map(([groupName, items]) => (
              <div key={groupName}>
                <div className="px-2 py-1 text-[10px] font-medium text-content-tertiary uppercase tracking-wide">
                  {groupName}
                </div>
                <div className="flex flex-col gap-0.5">
                  {items.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => handleSelect(conv.id)}
                      className={`group text-left px-2 py-2 rounded-md transition-all duration-150 relative ${
                        selectedConversationId === conv.id
                          ? 'bg-white text-content-primary shadow-[0_2px_8px_rgba(0,0,0,0.08)] -translate-y-0.5'
                          : 'text-content-tertiary hover:bg-[#EFEFEF] hover:text-content-secondary'
                      }`}
                    >
                      {/* 标题行 */}
                      <div className="flex items-center gap-1">
                        <EditableTitle
                          title={conv.title}
                          isEditing={editingId === conv.id}
                          onStartEdit={() => setEditingId(conv.id)}
                          onSave={(title) => handleSaveTitle(conv.id, title)}
                          onCancel={() => setEditingId(null)}
                          onDetail={() => {
                            setDetailConversation(conv)
                            setDetailOpen(true)
                          }}
                          onDelete={() => onDeleteConversation?.(conv.id)}
                        />
                      </div>

                      {/* 预览和时间 */}
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-content-tertiary truncate flex-1 mr-2">
                          {conv.last_message_preview || '还没有消息...'}
                        </span>
                        <span className="text-[10px] text-content-tertiary shrink-0">
                          {formatTime(conv.updated_at)}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Logout */}
      <button
        onClick={() => {
          onLogout()
          onMobileClose?.()
        }}
        className="flex items-center gap-2 px-2.5 py-2 rounded-md text-xs text-content-secondary hover:bg-surface-page transition-all duration-150 mt-2"
      >
        <LogOut size={16} />
        退出
      </button>
    </>
  )

  return (
    <>
      <ConversationDetailDrawer
        conversation={detailConversation}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      />
      {/* Desktop sidebar */}
      <aside
        className="hidden md:flex w-64 h-full flex-col bg-white/72 border-r border-white/50 shadow-elevated rounded-r-2xl p-4"
        style={{ backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' }}
      >
        {sidebarContent}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 z-40 md:hidden"
            onClick={onMobileClose}
          />
          {/* Drawer */}
          <aside
            className="fixed left-0 top-0 h-full w-64 flex flex-col bg-white/90 border-r border-white/50 shadow-floating p-4 z-50 md:hidden"
            style={{ backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' }}
          >
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  )
}
