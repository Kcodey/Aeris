import React from 'react'
import { Bot, User, FileText, FileSpreadsheet, FileImage, File } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Image } from 'antd'

interface FileRecord {
  id: number
  original_name: string
  mime_type?: string
  size_display?: string
}

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  file_ids?: number[]
  file_records?: FileRecord[]
}

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  filePreviews?: Record<number, string>
}

// 根据 MIME 类型返回对应的文件图标
const getFileIcon = (mimeType?: string) => {
  if (mimeType?.startsWith('image/')) return <FileImage size={18} className="text-brand" />
  if (mimeType?.includes('spreadsheet') || mimeType?.includes('excel')) return <FileSpreadsheet size={18} className="text-green-600" />
  if (mimeType?.includes('pdf') || mimeType?.includes('word') || mimeType?.includes('document')) return <FileText size={18} className="text-blue-600" />
  return <File size={18} className="text-content-tertiary" />
}

// 文件附件卡片
const FileAttachmentCard: React.FC<{ file: FileRecord; previewUrl?: string }> = ({ file, previewUrl }) => {
  const isImage = file.mime_type?.startsWith('image/')

  if (isImage && previewUrl) {
    return (
      <div className="flex items-center gap-2 bg-white/80 border border-border rounded-lg px-3 py-2 shadow-subtle">
        <Image src={previewUrl} width={40} height={40} className="rounded object-cover" preview />
        <div className="flex flex-col min-w-0">
          <span className="text-xs text-content-primary truncate">{file.original_name}</span>
          <span className="text-[10px] text-content-tertiary">{file.size_display || '图片'}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 bg-white/80 border border-border rounded-lg px-3 py-2 shadow-subtle">
      {getFileIcon(file.mime_type)}
      <div className="flex flex-col min-w-0">
        <span className="text-xs text-content-primary truncate">{file.original_name}</span>
        <span className="text-[10px] text-content-tertiary">{file.size_display || '文件'}</span>
      </div>
    </div>
  )
}

// 简化文件附件提示（只有 file_ids 时）
const FileAttachmentHint: React.FC<{ count: number }> = ({ count }) => (
  <div className="flex items-center gap-1.5 bg-white/60 border border-border rounded-lg px-3 py-1.5 w-fit">
    <File size={14} className="text-content-tertiary" />
    <span className="text-[11px] text-content-secondary">附带 {count} 个文件</span>
  </div>
)

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isStreaming = false,
  filePreviews = {},
}) => {
  const isUser = message.role === 'user'

  // 判断是否有文件附件
  const hasFileRecords = message.file_records && message.file_records.length > 0
  const hasFileIds = message.file_ids && message.file_ids.length > 0
  const hasAttachments = hasFileRecords || hasFileIds

  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse self-end' : ''} max-w-[80%]`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-border text-content-secondary'
            : 'bg-brand text-white shadow-glow'
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Bubble + Attachments */}
      <div className="flex flex-col gap-1.5">
        {/* Message Bubble */}
        <div
          className={`px-4 py-3 text-body leading-relaxed shadow-subtle ${
            isUser
              ? 'bg-content-primary text-white rounded-2xl rounded-tr-sm'
              : 'bg-brand-light border border-amber-100 rounded-2xl rounded-tl-sm text-[#44403c]'
          }`}
        >
          {isUser ? (
            message.content
          ) : isStreaming && !message.content ? (
            <span className="inline-flex items-center gap-1 text-content-tertiary">
              AI 思考中
              <span className="inline-flex">
                <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
              </span>
            </span>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" className="text-brand underline" />
                ),
                img: ({ src, alt }) => (
                  <Image src={src} alt={alt} className="max-w-full rounded-md" preview />
                ),
                pre: ({ children }) => <pre className="bg-black/5 rounded-md p-3 overflow-auto text-xs">{children}</pre>,
                code: ({ children }) => <code className="bg-black/5 rounded px-1 py-0.5 text-xs">{children}</code>,
                table: ({ children }) => (
                  <table className="table-auto w-full border-collapse text-xs my-2 border border-gray-200">{children}</table>
                ),
                thead: ({ children }) => <thead className="bg-gray-100">{children}</thead>,
                th: ({ children }) => (
                  <th className="border border-gray-200 px-2 py-1 text-left font-medium">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="border border-gray-200 px-2 py-1">{children}</td>
                ),
                tr: ({ children }) => <tr className="even:bg-gray-50">{children}</tr>,
              }}
            >
              {message.content || ''}
            </ReactMarkdown>
          )}
        </div>

        {/* File Attachments (单独显示，不和文字混在一起) */}
        {isUser && hasAttachments && (
          <div className="flex flex-col gap-1.5">
            {/* 有完整文件记录时显示卡片 */}
            {hasFileRecords && message.file_records!.map((file) => (
              <FileAttachmentCard
                key={file.id}
                file={file}
                previewUrl={filePreviews[file.id]}
              />
            ))}
            {/* 只有 file_ids 时显示简化提示 */}
            {!hasFileRecords && hasFileIds && (
              <FileAttachmentHint count={message.file_ids!.length} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
