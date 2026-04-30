import React, { useState, useRef, useEffect } from 'react'
import { Bubble } from '@ant-design/x'
import { Button, Input, Space, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import type { BubbleDataType } from '@ant-design/x/es/bubble'
import { chatApi } from '../../services/chat'
import { Message } from '../../types/chat'

interface ChatWindowProps {
  conversationId?: number
}

const ChatWindow: React.FC<ChatWindowProps> = ({ conversationId }) => {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [typingMessageId, setTypingMessageId] = useState<number | null>(null)
  const [pendingAiMessageId, setPendingAiMessageId] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversation messages
  useEffect(() => {
    if (conversationId) {
      setTypingMessageId(null)
      setPendingAiMessageId(null)
      loadMessages()
    }
  }, [conversationId])

  // Clear typing effect after 2 seconds
  useEffect(() => {
    if (typingMessageId !== null) {
      const timer = setTimeout(() => {
        setTypingMessageId(null)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [typingMessageId])

  const loadMessages = async () => {
    if (!conversationId) return
    try {
      const response = await chatApi.getConversation(conversationId)
      setMessages(response.data.messages || [])
    } catch (error) {
      console.error('Failed to load messages:', error)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!inputValue.trim() || !conversationId) return

    const content = inputValue
    setInputValue('')
    setLoading(true)
    setTypingMessageId(null) // Clear previous typing

    // Add user message immediately
    const tempMessage: Message = {
      id: Date.now(),
      conversation_id: conversationId,
      role: 'user',
      content: content,
      created_at: new Date().toISOString(),
    }

    // Add AI loading placeholder
    const loadingAiId = Date.now() + 1
    const loadingAiMessage: Message = {
      id: loadingAiId,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }
    setPendingAiMessageId(loadingAiId)
    setMessages((prev) => [...prev, tempMessage, loadingAiMessage])

    try {
      const response = await chatApi.sendMessage(conversationId, {
        message: content,
      })
      const aiMsg = response.data.message
      if (aiMsg) {
        // Replace loading placeholder with actual response
        setMessages((prev) => prev.map((msg) => (msg.id === loadingAiId ? aiMsg : msg)))
        setTypingMessageId(aiMsg.id)
      }
    } catch (error) {
      message.error('发送消息失败')
      // Remove loading placeholder on error
      setMessages((prev) => prev.filter((msg) => msg.id !== loadingAiId))
      console.error('Failed to send message:', error)
    } finally {
      setLoading(false)
      setPendingAiMessageId(null)
    }
  }

  const items: BubbleDataType[] = messages.map((msg) => ({
    key: msg.id,
    role: msg.role === 'user' ? 'user' : 'ai',
    content: msg.content || '',
    // Show loading for the pending AI placeholder
    ...(msg.role !== 'user' && msg.id === pendingAiMessageId
      ? { loading: true }
      : {}),
    // Only the newly received AI message gets typing animation
    ...(msg.role !== 'user' && msg.id === typingMessageId
      ? { typing: { step: 2, interval: 50 } }
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
            },
          }}
        />
        <div ref={messagesEndRef} />
      </div>

      <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={handleSend}
            placeholder="输入消息..."
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
          >
            发送
          </Button>
        </Space.Compact>
      </div>
    </div>
  )
}

export default ChatWindow
