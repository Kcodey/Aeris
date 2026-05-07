import React, { useState, useRef, useEffect } from 'react'
import { message } from 'antd'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'
import { EmptyState } from './EmptyState'
import { chatApi, createWebSocket } from '../../services/chat'
import { fileApi } from '../../services/files'
import { getToken } from '../../utils/token'
import { Message } from '../../types/chat'
import { FileRecord } from '../../types/file'

const MAX_TOTAL_FILE_SIZE = 2 * 1024 * 1024  // 2MB

interface ChatWindowProps {
  conversationId?: number
  onMessageSent?: () => void
  onCreateConversation?: () => void
}

const ChatWindow: React.FC<ChatWindowProps> = ({ conversationId, onMessageSent, onCreateConversation }) => {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState<FileRecord[]>([])
  const [filePreviews, setFilePreviews] = useState<Record<number, string>>({})
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (conversationId) {
      setIsStreaming(false)
      setAttachedFiles([])
      loadMessages()
    }
  }, [conversationId])

  useEffect(() => {
    const token = getToken()
    if (!token) return

    const ws = createWebSocket(token)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const chunk = JSON.parse(event.data)
      switch (chunk.type) {
        case 'content':
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...last,
                content: (last.content || '') + chunk.content,
              }
              return updated
            }
            return prev
          })
          break
        case 'tool_call':
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...last,
                content: (last.content || '') + `\n[调用工具: ${chunk.name}]`,
              }
              return updated
            }
            return prev
          })
          break
        case 'done':
          setIsStreaming(false)
          setLoading(false)
          onMessageSent?.()
          break
        case 'error':
          setIsStreaming(false)
          setLoading(false)
          break
      }
    }

    ws.onerror = () => {
      if (wsRef.current === ws) {
        setIsStreaming(false)
        setLoading(false)
      }
    }

    ws.onclose = () => {
      if (wsRef.current === ws) {
        setIsStreaming(false)
        setLoading(false)
      }
    }

    return () => {
      wsRef.current = null
      ws.close()
    }
  }, [])

  const loadMessages = async () => {
    if (!conversationId) return
    try {
      const response = await chatApi.getConversation(conversationId)
      setMessages(response.data.messages || [])
    } catch (error) {
      console.error('Failed to load messages:', error)
    }
  }

  const handleUpload = async (file: File) => {
    if (!conversationId) return

    // 检查单个文件大小
    if (file.size > MAX_TOTAL_FILE_SIZE) {
      message.error(`文件大小不能超过 2MB（当前 ${(file.size / 1024 / 1024).toFixed(2)}MB）`)
      return
    }

    // 检查总大小
    const currentTotal = attachedFiles.reduce((sum, f) => sum + (f.size_bytes || 0), 0)
    if (currentTotal + file.size > MAX_TOTAL_FILE_SIZE) {
      message.error('已附加文件总大小不能超过 2MB，请先删除部分文件')
      return
    }

    const previewUrl = URL.createObjectURL(file)
    setUploading(true)
    try {
      const response = await fileApi.uploadFile(file, conversationId)
      setAttachedFiles((prev) => [...prev, response.data])
      setFilePreviews((prev) => ({ ...prev, [response.data.id]: previewUrl }))
    } catch (error) {
      URL.revokeObjectURL(previewUrl)
    } finally {
      setUploading(false)
    }
  }

  const removeAttachedFile = async (fileId: number) => {
    try {
      await fileApi.deleteFile(fileId)
      setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))
    } catch (error) {
      console.error('Failed to delete file:', error)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (!inputValue.trim() || !conversationId || isStreaming) return

    const content = inputValue
    setInputValue('')
    setLoading(true)
    setIsStreaming(true)

    const tempUserMsg: Message = {
      id: Date.now(),
      conversation_id: conversationId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      file_records: attachedFiles,
    }

    const aiPlaceholder: Message = {
      id: Date.now() + 1,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, tempUserMsg, aiPlaceholder])

    const currentFileIds = attachedFiles.map((f) => f.id)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'message',
          conversation_id: conversationId,
          content,
          file_ids: currentFileIds,
        })
      )
      setAttachedFiles([])
    } else {
      setIsStreaming(false)
      setLoading(false)
    }
  }

  if (!conversationId) {
    return (
      <div className="h-full">
        <EmptyState onCreateConversation={onCreateConversation} />
      </div>
    )
  }

  // Filter messages to only show user/assistant for bubbles
  const displayMessages = messages.filter(
    (msg) => msg.role === 'user' || msg.role === 'assistant'
  )

  return (
    <div className="h-full flex flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-auto px-5 py-4 flex flex-col gap-4">
        {displayMessages.map((msg, index) => (
          <MessageBubble
            key={msg.id}
            message={msg as any}
            isStreaming={isStreaming && index === displayMessages.length - 1}
            filePreviews={filePreviews}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        onUpload={handleUpload}
        attachedFiles={attachedFiles}
        onRemoveFile={removeAttachedFile}
        loading={loading}
        uploading={uploading}
        disabled={!conversationId}
      />
    </div>
  )
}

export default ChatWindow
