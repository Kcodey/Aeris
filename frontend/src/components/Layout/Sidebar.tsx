import React from 'react'
import { MessageSquare, BarChart3, LogOut, Plus } from 'lucide-react'

interface Conversation {
  id: number
  title: string | null
  updated_at: string | null
}

interface SidebarProps {
  activeRoute: string
  conversations: Conversation[]
  selectedConversationId: number | null
  onNavigate: (route: string) => void
  onSelectConversation: (id: number) => void
  onCreateConversation: () => void
  onLogout: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeRoute,
  conversations,
  selectedConversationId,
  onNavigate,
  onSelectConversation,
  onCreateConversation,
  onLogout,
}) => {
  const navItems = [
    { key: '/', label: '对话', icon: MessageSquare },
    { key: '/monitoring', label: '监控', icon: BarChart3 },
  ]

  return (
    <aside
      className="w-60 h-full flex flex-col bg-white/72 border-r border-white/50 shadow-elevated rounded-r-2xl p-4"
      style={{ backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' }}
    >
      {/* Brand */}
      <div className="px-2 mb-4 flex items-center justify-between">
        <span className="text-sm font-bold text-brand">Aeris</span>
        <button
          onClick={onCreateConversation}
          className="w-7 h-7 rounded-lg bg-brand-light flex items-center justify-center text-brand hover:bg-brand/10 transition-colors"
          title="新建对话"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 mb-3">
        {navItems.map((item) => {
          const isActive = activeRoute === item.key
          const Icon = item.icon
          return (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-md text-xs font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-brand-light text-content-primary font-semibold'
                  : 'text-content-secondary hover:bg-surface-page'
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
        <div className="flex flex-col gap-0.5">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`text-left px-2 py-1.5 rounded-md transition-all duration-150 truncate ${
                selectedConversationId === conv.id
                  ? 'bg-brand-light text-content-primary font-medium'
                  : 'text-content-tertiary hover:bg-surface-page hover:text-content-secondary'
              }`}
            >
              <div className="truncate text-xs">{conv.title || '未命名对话'}</div>
              <div className="text-[10px] text-content-tertiary mt-0.5">
                {conv.updated_at
                  ? new Date(conv.updated_at).toLocaleDateString()
                  : ''}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Logout */}
      <button
        onClick={onLogout}
        className="flex items-center gap-2 px-2.5 py-2 rounded-md text-xs text-content-secondary hover:bg-surface-page transition-all duration-150 mt-2"
      >
        <LogOut size={16} />
        退出
      </button>
    </aside>
  )
}
