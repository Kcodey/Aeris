import React, { useState, useEffect } from 'react'
import { Layout, List, Button, Input, Typography, message, Dropdown, Modal, Checkbox, Space } from 'antd'
import { PlusOutlined, DeleteOutlined, CheckSquareOutlined } from '@ant-design/icons'
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
  const [batchMode, setBatchMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

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

  const handleDelete = async (conversation: Conversation) => {
    Modal.confirm({
      title: '删除对话',
      content: `确定删除对话「${conversation.title || '未命名对话'}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      async onOk() {
        try {
          await chatApi.deleteConversation(conversation.id)
          setConversations((prev) => prev.filter((c) => c.id !== conversation.id))
          if (selectedConversation === conversation.id) {
            const remaining = conversations.filter((c) => c.id !== conversation.id)
            setSelectedConversation(remaining.length > 0 ? remaining[0].id : null)
          }
          message.success('删除成功')
        } catch (error) {
          message.error('删除失败')
        }
      },
    })
  }

  const toggleBatchMode = () => {
    setBatchMode((prev) => !prev)
    setSelectedIds(new Set())
  }

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const selectAll = () => {
    setSelectedIds(new Set(conversations.map((c) => c.id)))
  }

  const clearAll = () => {
    setSelectedIds(new Set())
  }

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return
    Modal.confirm({
      title: '批量删除',
      content: `确定删除选中的 ${selectedIds.size} 个对话吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      async onOk() {
        try {
          const ids = Array.from(selectedIds)
          await Promise.all(ids.map((id) => chatApi.deleteConversation(id)))
          const remaining = conversations.filter((c) => !selectedIds.has(c.id))
          setConversations(remaining)
          if (selectedConversation !== null && selectedIds.has(selectedConversation)) {
            setSelectedConversation(remaining.length > 0 ? remaining[0].id : null)
          }
          setSelectedIds(new Set())
          setBatchMode(false)
          message.success(`已删除 ${ids.length} 个对话`)
        } catch (error) {
          message.error('批量删除失败')
        }
      },
    })
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
            style={{ marginBottom: 8 }}
          >
            新建对话
          </Button>
          <Button
            block
            icon={<CheckSquareOutlined />}
            onClick={toggleBatchMode}
          >
            {batchMode ? '完成' : '管理'}
          </Button>
        </div>
        {batchMode && (
          <div style={{ padding: '0 16px 8px', display: 'flex', gap: 8 }}>
            <Button size="small" onClick={selectAll}>全选</Button>
            <Button size="small" onClick={clearAll}>取消全选</Button>
          </div>
        )}
        <List
          dataSource={conversations}
          renderItem={(item) => (
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'delete',
                    label: '删除',
                    icon: <DeleteOutlined />,
                    danger: true,
                    onClick: () => handleDelete(item),
                  },
                ],
              }}
              trigger={batchMode ? [] : ['contextMenu']}
            >
              <List.Item
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  background: selectedConversation === item.id ? '#e6f7ff' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                }}
                onClick={() => {
                  if (batchMode) {
                    toggleSelect(item.id)
                  } else {
                    setSelectedConversation(item.id)
                  }
                }}
              >
                {batchMode && (
                  <Checkbox
                    checked={selectedIds.has(item.id)}
                    onChange={() => toggleSelect(item.id)}
                    style={{ marginRight: 8 }}
                    onClick={(e) => e.stopPropagation()}
                  />
                )}
                <Text ellipsis style={{ flex: 1 }}>
                  {item.title || '未命名对话'}
                </Text>
              </List.Item>
            </Dropdown>
          )}
        />
        {batchMode && (
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid #f0f0f0',
              background: '#fafafa',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: 14 }}>已选 {selectedIds.size} 项</span>
            <Space>
              <Button size="small" onClick={toggleBatchMode}>取消</Button>
              <Button
                size="small"
                type="primary"
                danger
                disabled={selectedIds.size === 0}
                onClick={handleBatchDelete}
              >
                删除 {selectedIds.size} 项
              </Button>
            </Space>
          </div>
        )}
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
