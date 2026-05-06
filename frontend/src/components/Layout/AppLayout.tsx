import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation, Routes, Route } from 'react-router-dom'
import { Menu } from 'lucide-react'
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
  const [mobileOpen, setMobileOpen] = useState(false)

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
    <div className="h-screen w-screen flex flex-col md:flex-row bg-surface-page overflow-hidden">
      {/* Mobile header */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-white/72 border-b border-white/50"
        style={{ backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' }}
      >
        <button
          onClick={() => setMobileOpen(true)}
          className="w-9 h-9 rounded-lg flex items-center justify-center text-content-secondary hover:bg-surface-page transition-colors"
        >
          <Menu size={20} />
        </button>
        <span className="text-sm font-bold text-brand">Aeris</span>
        <div className="w-9" />
      </div>

      <Sidebar
        activeRoute={location.pathname}
        conversations={conversations}
        selectedConversationId={selectedConversationId}
        onNavigate={handleNavigate}
        onSelectConversation={handleSelectConversation}
        onCreateConversation={handleCreateConversation}
        onLogout={onLogout}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />
      <main className="flex-1 m-0 md:m-4 md:rounded-xl overflow-hidden">
        <Routes>
          <Route path="/" element={<ChatPage selectedConversationId={selectedConversationId} />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default AppLayout
