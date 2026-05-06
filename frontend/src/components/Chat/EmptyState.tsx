import React from 'react'
import { MessageSquare } from 'lucide-react'

interface EmptyStateProps {
  onCreateConversation: () => void
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onCreateConversation }) => {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-3">
      <div className="w-16 h-16 rounded-2xl bg-brand-light flex items-center justify-center text-brand">
        <MessageSquare size={32} />
      </div>
      <h3 className="text-heading font-semibold text-content-primary">开始一段新对话</h3>
      <p className="text-caption text-content-secondary text-center max-w-[300px]">
        点击左侧「新建对话」或选择一个已有对话开始交流
      </p>
      <button
        onClick={onCreateConversation}
        className="mt-2 bg-brand text-white rounded-xl px-5 py-2.5 text-body font-medium shadow-glow transition-all duration-200 hover:bg-brand-dark hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(217,119,6,0.35)] active:translate-y-0"
      >
        新建对话
      </button>
    </div>
  )
}
