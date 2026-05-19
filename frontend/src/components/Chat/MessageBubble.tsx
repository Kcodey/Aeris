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

const TOOL_NAME_ALIAS: Record<string, string> = {
  rag_search: '知识库搜索',
  load_skill: '加载技能',
  bash: '执行命令',
  conversation_search: '对话搜索',
  schedule_create: '创建日程',
  schedule_list: '查看日程',
  schedule_delete: '删除日程',
  file_write: '写文件',
  file_list: '列出文件',
  inspect_excel: '分析 Excel',
}

interface ToolCall {
  id: string
  name: string
  arguments: string
  status: 'pending' | 'done'
  result?: string
}

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  file_ids?: number[]
  file_records?: FileRecord[]
  tool_calls?: ToolCall[]
}

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  filePreviews?: Record<number, string>
}

const getFileIcon = (mimeType?: string) => {
  if (mimeType?.startsWith('image/')) return <FileImage size={18} className="text-brand" />
  if (mimeType?.includes('spreadsheet') || mimeType?.includes('excel')) return <FileSpreadsheet size={18} className="text-green-600" />
  if (mimeType?.includes('pdf') || mimeType?.includes('word') || mimeType?.includes('document')) return <FileText size={18} className="text-blue-600" />
  return <File size={18} className="text-content-tertiary" />
}

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
  // const hasPendingTool = message.tool_calls?.some(tc => tc.status === 'pending')
  // 保留你正确的逻辑
  // const showEllipsis = isStreaming && !message.content
  const contentVisible = typeof message.content === 'string' && message.content.trim().length > 0
  const showEllipsis = isStreaming && !contentVisible

  const hasFileRecords = message.file_records && message.file_records.length > 0
  const hasFileIds = message.file_ids && message.file_ids.length > 0
  const hasAttachments = hasFileRecords || hasFileIds

  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse self-end' : ''} max-w-[80%]`}>
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-border text-content-secondary'
            : 'bg-brand text-white shadow-glow'
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className="flex flex-col gap-1.5">
        {/* 🔥 修复1：给气泡增加固定最小高度，永不塌陷（核心！） */}
        <div
          className={`px-4 py-3 text-body leading-relaxed shadow-subtle min-h-[24px] ${
            isUser
              ? 'bg-content-primary text-white rounded-2xl rounded-tr-sm'
              : 'bg-brand-light border border-amber-100 rounded-2xl rounded-tl-sm text-[#44403c]'
          }`}
        >
          {isUser ? (
            message.content
          ) : showEllipsis ? (
            <span className="inline-flex">
              <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
            </span>
          ) : (
            // 🔥 修复2：兜底渲染！空内容时展示透明占位符，彻底消灭空白
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
              {/* 兜底：无内容时显示一个透明的点，占位不显示 */}
              {message.content || <span className="opacity-0">.</span>}
            </ReactMarkdown>
          )}
        </div>

        {isUser && hasAttachments && (
          <div className="flex flex-col gap-1.5">
            {hasFileRecords && message.file_records!.map((file) => (
              <FileAttachmentCard
                key={file.id}
                file={file}
                previewUrl={filePreviews[file.id]}
              />
            ))}
            {!hasFileRecords && hasFileIds && (
              <FileAttachmentHint count={message.file_ids!.length} />
            )}
          </div>
        )}

        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="flex flex-col gap-1.5">
            {message.tool_calls.map((tc) => (
              <div key={tc.id} className="flex items-center gap-2 text-xs">
                {tc.status === 'pending' ? (
                  <div className="flex items-center gap-1.5 text-amber-600">
                    <span className="animate-spin">⟳</span>
                    <span className="bg-amber-50 px-2 py-0.5 rounded">{TOOL_NAME_ALIAS[tc.name] || tc.name}</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-green-600">
                    <span>✓</span>
                    <span className="bg-green-50 px-2 py-0.5 rounded">{TOOL_NAME_ALIAS[tc.name] || tc.name}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
