import React from 'react'
import ChatWindow from '../components/Chat/ChatWindow'

interface ChatPageProps {
  selectedConversationId?: number | null
  onMessageSent?: () => void
  onCreateConversation?: () => void
}

const ChatPage: React.FC<ChatPageProps> = ({ selectedConversationId, onMessageSent, onCreateConversation }) => {
  return (
    <div className="h-full">
      <ChatWindow
        conversationId={selectedConversationId || undefined}
        onMessageSent={onMessageSent}
        onCreateConversation={onCreateConversation}
      />
    </div>
  )
}

export default ChatPage
