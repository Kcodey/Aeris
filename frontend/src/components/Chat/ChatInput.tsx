import React from 'react'
import { Paperclip, Send } from 'lucide-react'

interface FileRecord {
  id: number
  original_name: string
  mime_type?: string
  size_display?: string
}

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onUpload: (file: File) => void
  attachedFiles: FileRecord[]
  selectedFileIds: Set<number>  // ← 新增：选中的文件ID
  onToggleFile: (fileId: number) => void  // ← 新增：切换选中
  onDetachFile: (fileId: number) => void  // ← 新增：取消引用
  loading?: boolean
  uploading?: boolean
  disabled?: boolean
}

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  onUpload,
  attachedFiles,
  selectedFileIds,
  onToggleFile,
  onDetachFile,
  loading = false,
  uploading = false,
  disabled = false,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onUpload(file)
    }
    e.target.value = ''
  }

  const selectedCount = selectedFileIds.size
  const totalCount = attachedFiles.length

  return (
    <div className="border-t border-[#f0f0f0] px-5 py-4">
      {/* Attached files with selection */}
      {attachedFiles.length > 0 && (
        <div className="mb-2.5">
          {/* Selection hint */}
          <div className="text-label text-content-secondary mb-1.5">
            点击文件选择本次引用 ({selectedCount}/{totalCount})
          </div>
          <div className="flex gap-2 flex-wrap">
            {attachedFiles.map((file) => {
              const isSelected = selectedFileIds.has(file.id)
              return (
                <div
                  key={file.id}
                  onClick={() => onToggleFile(file.id)}
                  className={`
                    flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-label cursor-pointer
                    transition-all duration-150
                    ${isSelected
                      ? 'bg-brand/10 border-2 border-brand text-brand'
                      : 'bg-surface-page border-2 border-border text-content-secondary hover:border-brand/50'
                    }
                  `}
                >
                  {/* Selection indicator */}
                  <span className={`
                    w-4 h-4 rounded flex items-center justify-center text-xs
                    ${isSelected ? 'bg-brand text-white' : 'bg-white border border-border'}
                  `}>
                    {isSelected ? '✓' : ''}
                  </span>
                  <span className="truncate max-w-[120px]">{file.original_name}</span>
                  {/* Detach button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDetachFile(file.id)
                    }}
                    className="text-content-tertiary hover:text-error transition-colors ml-1"
                    title="从引用中移除"
                  >
                    ✕
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Input container */}
      <div className="flex items-end gap-2 bg-surface-page border border-border rounded-2xl px-3.5 py-2.5 transition-all duration-200 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/10">
        {/* Upload button */}
        <label className="w-8 h-8 rounded-xl bg-surface-card border border-border flex items-center justify-center text-content-secondary cursor-pointer flex-shrink-0 hover:bg-surface-page transition-colors">
          <Paperclip size={16} />
          <input
            type="file"
            className="hidden"
            onChange={handleFileChange}
            disabled={uploading || loading || disabled}
          />
        </label>

        {/* Text input */}
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息..."
          rows={1}
          disabled={loading || disabled}
          className="flex-1 bg-transparent border-none outline-none resize-none text-body text-content-primary placeholder-content-tertiary py-1.5 max-h-32"
          style={{ minHeight: '24px' }}
        />

        {/* Send button */}
        <button
          onClick={onSend}
          disabled={loading || disabled || (!value.trim() && selectedFileIds.size === 0)}
          className="w-8 h-8 rounded-xl bg-brand text-white flex items-center justify-center flex-shrink-0 shadow-glow transition-all duration-200 hover:bg-brand-dark hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(217,119,6,0.35)] active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
