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
  onRemoveFile: (fileId: number) => void
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
  onRemoveFile,
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

  return (
    <div className="border-t border-[#f0f0f0] px-5 py-4">
      {/* Attached files */}
      {attachedFiles.length > 0 && (
        <div className="flex gap-2 mb-2.5 flex-wrap">
          {attachedFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-1.5 bg-surface-page border border-border rounded-lg px-2.5 py-1.5 text-label text-[#57534e]"
            >
              <span className="truncate max-w-[120px]">{file.original_name}</span>
              <button
                onClick={() => onRemoveFile(file.id)}
                className="text-content-tertiary hover:text-error transition-colors"
              >
                ✕
              </button>
            </div>
          ))}
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
          disabled={loading || disabled || (!value.trim() && attachedFiles.length === 0)}
          className="w-8 h-8 rounded-xl bg-brand text-white flex items-center justify-center flex-shrink-0 shadow-glow transition-all duration-200 hover:bg-brand-dark hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(217,119,6,0.35)] active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
