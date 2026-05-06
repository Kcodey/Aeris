import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation, Routes, Route } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import ChatPage from '../../pages/ChatPage'
import MonitoringPage from '../../pages/MonitoringPage'
import { chatApi } from '../../services/chat'
import { Conversation } from '../../types/chat'

interface AppLayoutProps {
  onLogout: () => void
}

const AppLayout: React.FC<AppLayoutProps> = ({ onLogout }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const response = await chatApi.getConversations()
      setConversations(response.data)
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }

  const handleNavigate = (route: string) => {
    navigate(route)
  }

  const handleSelectConversation = (id: number) => {
    setSelectedConversationId(id)
    navigate('/')
  }

  const handleCreateConversation = async () => {
    try {
      const response = await chatApi.createConversation()
      setConversations((prev) => [response.data, ...prev])
      setSelectedConversationId(response.data.id)
      navigate('/')
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }

  return (
    <div className="h-screen w-screen flex bg-surface-page overflow-hidden">
      <Sidebar
        activeRoute={location.pathname}
        conversations={conversations}
        selectedConversationId={selectedConversationId}
        onNavigate={handleNavigate}
        onSelectConversation={handleSelectConversation}
        onCreateConversation={handleCreateConversation}
        onLogout={onLogout}
      />
      <main className="flex-1 m-4 bg-surface-card rounded-xl shadow-subtle overflow-hidden">
        <Routes>
          <Route path="/" element={<ChatPage selectedConversationId={selectedConversationId} />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default AppLayout
