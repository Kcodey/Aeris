import React, { useState, useRef, useEffect } from 'react'
import { Bubble } from '@ant-design/x'
import { Button, Input, Space, message, Upload, Tag, Tooltip } from 'antd'
import { SendOutlined, PaperClipOutlined, FileOutlined, PictureOutlined } from '@ant-design/icons'
import type { BubbleDataType } from '@ant-design/x/es/bubble'
import ReactMarkdown from 'react-markdown'
import { chatApi, createWebSocket } from '../../services/chat'
import { Message } from '../../types/chat'
import { getToken } from '../../utils/token'
import { fileApi } from '../../services/files'
import { FileRecord } from '../../types/file'

const CopyButton: React.FC<{ text: string }> = ({ text }) => {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      message.error('复制失败')
    }
  }
  return (
    <Button
      size="small"
      style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}
      onClick={handleCopy}
    >
      {copied ? '已复制' : '复制'}
    </Button>
  )
}

interface ChatWindowProps {
  conversationId?: number
}

const ChatWindow: React.FC<ChatWindowProps> = ({ conversationId }) => {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState<FileRecord[]>([])
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Load conversation messages
  useEffect(() => {
    if (conversationId) {
      setIsStreaming(false)
      setAttachedFiles([])
      loadMessages()
    }
  }, [conversationId])

  // WebSocket connection — established once, reused across conversations
  useEffect(() => {
    const token = getToken()
    if (!token) return

    const ws = createWebSocket(token)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const chunk = JSON.parse(event.data)

      switch (chunk.type) {
        case 'content':
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1]
            if (lastMsg && lastMsg.role === 'assistant') {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...lastMsg,
                content: (lastMsg.content || '') + chunk.content,
              }
              return updated
            }
            return prev
          })
          break
        case 'tool_call':
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1]
            if (lastMsg && lastMsg.role === 'assistant') {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...lastMsg,
                content: (lastMsg.content || '') + `\n[调用工具: ${chunk.name}]`,
              }
              return updated
            }
            return prev
          })
          break
        case 'done':
          setIsStreaming(false)
          setLoading(false)
          break
        case 'error':
          message.error(chunk.error || '流式输出出错')
          setIsStreaming(false)
          setLoading(false)
          break
      }
    }

    ws.onerror = () => {
      // Only show error if this is still the active socket
      if (wsRef.current === ws) {
        message.error('WebSocket 连接出错')
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
    if (!conversationId) return false
    setUploading(true)
    try {
      const response = await fileApi.uploadFile(file, conversationId)
      setAttachedFiles((prev) => [...prev, { ...response.data, is_image: response.data.mime_type?.startsWith('image/') }])
      message.success(`已上传: ${response.data.original_name}`)
    } catch (error) {
      message.error('上传失败')
    } finally {
      setUploading(false)
    }
    return false
  }

  const removeAttachedFile = async (fileId: number) => {
    try {
      await fileApi.deleteFile(fileId)
      setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))
    } catch (error) {
      message.error('删除失败')
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

    // Add user message immediately
    const tempUserMsg: Message = {
      id: Date.now(),
      conversation_id: conversationId,
      role: 'user',
      content: content,
      created_at: new Date().toISOString(),
    }

    // Add AI placeholder
    const aiPlaceholder: Message = {
      id: Date.now() + 1,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, tempUserMsg, aiPlaceholder])

    // Send via WebSocket
    const currentFileIds = attachedFiles.map((f) => f.id)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'message',
          conversation_id: conversationId,
          content: content,
          file_ids: currentFileIds,
        })
      )
      setAttachedFiles([])
    } else {
      message.error('WebSocket 未连接')
      setIsStreaming(false)
      setLoading(false)
    }
  }

  const items: BubbleDataType[] = messages.map((msg) => ({
    key: msg.id,
    role: msg.role === 'user' ? 'user' : 'ai',
    content: msg.content || '',
    // Show loading for the AI placeholder while streaming
    ...(msg.role !== 'user' && msg.content === '' && isStreaming
      ? { loading: true }
      : {}),
  }))

  if (!conversationId) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span style={{ color: '#999' }}>选择一个对话或创建新对话</span>
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        <Bubble.List
          items={items}
          roles={{
            user: {
              placement: 'end',
              avatar: { icon: '👤', style: { background: '#87d068' } },
            },
            ai: {
              placement: 'start',
              avatar: { icon: '🤖', style: { background: '#1677ff' } },
              messageRender: (content) => (
                <ReactMarkdown
                  components={{
                    a: ({ node, ...props }) => (
                      <a {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                    pre: ({ children }) => {
                      let codeText = ''
                      React.Children.forEach(children, (child) => {
                        if (React.isValidElement(child) && child.type === 'code') {
                          codeText = String(child.props.children || '')
                        }
                      })
                      return (
                        <div style={{ position: 'relative' }}>
                          <CopyButton text={codeText} />
                          <pre>{children}</pre>
                        </div>
                      )
                    },
                  }}
                >
                  {String(content || '')}
                </ReactMarkdown>
              ),
            },
          }}
        />
        <div ref={messagesEndRef} />
      </div>

      {attachedFiles.length > 0 && (
        <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {attachedFiles.map((file) => (
            <Tag
              key={file.id}
              icon={file.is_image ? <PictureOutlined /> : <FileOutlined />}
              closable
              onClose={(e) => {
                e.stopPropagation()
                removeAttachedFile(file.id)
              }}
              style={{ display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <Tooltip title={`${file.original_name} (${file.size_display})`}>
                <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {file.original_name}
                </span>
              </Tooltip>
            </Tag>
          ))}
        </div>
      )}

      <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
        <Space.Compact style={{ width: '100%' }}>
          <Upload beforeUpload={handleUpload} showUploadList={false} disabled={uploading || loading || isStreaming}>
            <Button icon={<PaperClipOutlined />} disabled={uploading || loading || isStreaming} loading={uploading} />
          </Upload>
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={handleSend}
            placeholder="输入消息..."
            disabled={loading || isStreaming}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading || isStreaming}
          >
            发送
          </Button>
        </Space.Compact>
      </div>
    </div>
  )
}

export default ChatWindow
