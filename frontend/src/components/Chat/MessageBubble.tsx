import React from 'react'
import { Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
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
  file_records?: FileRecord[]
}

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  filePreviews?: Record<number, string>
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isStreaming = false,
  filePreviews = {},
}) => {
  const isUser = message.role === 'user'

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

      {/* Bubble */}
      <div className="flex flex-col">
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
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" className="text-brand underline" />
                ),
                img: ({ src, alt }) => (
                  <Image src={src} alt={alt} className="max-w-full rounded-md" preview />
                ),
                pre: ({ children }) => <pre className="bg-black/5 rounded-md p-3 overflow-auto text-xs">{children}</pre>,
                code: ({ children }) => <code className="bg-black/5 rounded px-1 py-0.5 text-xs">{children}</code>,
              }}
            >
              {message.content || ''}
            </ReactMarkdown>
          )}
        </div>

        {/* Attached images for user */}
        {isUser && message.file_records && message.file_records.length > 0 && (
          <div className="flex gap-2 mt-2 flex-wrap">
            {message.file_records.map((file) =>
              file.mime_type?.startsWith('image/') && filePreviews[file.id] ? (
                <Image
                  key={file.id}
                  src={filePreviews[file.id]}
                  width={120}
                  className="rounded-md object-cover"
                  preview
                />
              ) : null
            )}
          </div>
        )}
      </div>
    </div>
  )
}
