import React, { useState, useRef, useEffect } from 'react'
import { Bubble, useXAgent, useXChat } from '@ant-design/x'
import { Button, Input, Space, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import type { BubbleDataType } from '@ant-design/x/es/bubble'

interface ChatWindowProps {
  conversationId?: number
}

const ChatWindow: React.FC<ChatWindowProps> = ({ conversationId }) => {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const agent = useXAgent<string>({
    request: async ({ message }, { onSuccess, onError }) => {
      try {
        // TODO: Implement WebSocket or API call
        // For now, simulate response
        setTimeout(() => {
          onSuccess(`Response to: ${message}`)
        }, 1000)
      } catch (error) {
        onError(error as Error)
      }
    },
  })

  const { onRequest, messages } = useXChat({ agent })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (!inputValue.trim()) return
    onRequest(inputValue)
    setInputValue('')
  }

  const items: BubbleDataType[] = messages.map((msg, index) => ({
    key: index,
    role: msg.status === 'local' ? 'user' : 'ai',
    content: msg.message,
  }))

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
              typing: { step: 2, interval: 50 },
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
