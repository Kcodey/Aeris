import React from 'react'
import ChatWindow from '../components/Chat/ChatWindow'

interface ChatPageProps {
  selectedConversationId?: number | null
}

const ChatPage: React.FC<ChatPageProps> = ({ selectedConversationId }) => {
  return (
    <div className="h-full">
      <ChatWindow conversationId={selectedConversationId || undefined} />
    </div>
  )
}

export default ChatPage
