import React, { useState, useEffect } from 'react'
import { Layout, List, Button, Input, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import ChatWindow from '../components/Chat/ChatWindow'
import { chatApi } from '../services/chat'
import { Conversation } from '../types/chat'

const { Sider, Content } = Layout
const { Text } = Typography

const ChatPage: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [newTitle, setNewTitle] = useState('')

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const response = await chatApi.getConversations()
      setConversations(response.data)
      if (response.data.length > 0 && !selectedConversation) {
        setSelectedConversation(response.data[0].id)
      }
    } catch (error) {
      message.error('加载对话列表失败')
    }
  }

  const createConversation = async () => {
    setLoading(true)
    try {
      const response = await chatApi.createConversation(
        newTitle ? { title: newTitle } : {}
      )
      setConversations([response.data, ...conversations])
      setSelectedConversation(response.data.id)
      setNewTitle('')
    } catch (error) {
      message.error('创建对话失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout style={{ height: '100%', background: '#fff', overflow: 'hidden' }}>
      <Sider
        width={250}
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
          height: '100%',
          overflow: 'auto',
        }}
      >
        <div style={{ padding: 16 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={createConversation}
            loading={loading}
          >
            新建对话
          </Button>
        </div>
        <List
          dataSource={conversations}
          renderItem={(item) => (
            <List.Item
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                background: selectedConversation === item.id ? '#e6f7ff' : 'transparent',
              }}
              onClick={() => setSelectedConversation(item.id)}
            >
              <Text ellipsis style={{ width: '100%' }}>
                {item.title || '未命名对话'}
              </Text>
            </List.Item>
          )}
        />
      </Sider>
      <Content style={{ height: '100%', overflow: 'hidden' }}>
        {selectedConversation ? (
          <ChatWindow conversationId={selectedConversation} />
        ) : (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Text type="secondary">选择或创建一个对话</Text>
          </div>
        )}
      </Content>
    </Layout>
  )
}

export default ChatPage
