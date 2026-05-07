import api from './api'
import {
  Conversation,
  ConversationWithMessages,
  ChatRequest,
  ChatResponse,
} from '../types/chat'

export const chatApi = {
  getConversations: (params?: { skip?: number; limit?: number }) =>
    api.get<Conversation[]>('/conversations', { params }),

  createConversation: (data: { title?: string } = {}) =>
    api.post<Conversation>('/conversations', data),

  getConversation: (id: number) =>
    api.get<ConversationWithMessages>(`/conversations/${id}`),

  updateConversation: (id: number, data: { title?: string }) =>
    api.patch<Conversation>(`/conversations/${id}`, data),

  sendMessage: (conversationId: number, data: ChatRequest) =>
    api.post<ChatResponse>(`/conversations/${conversationId}/messages`, data),

  deleteConversation: (id: number) =>
    api.delete(`/conversations/${id}`),
}

export const createWebSocket = (token: string): WebSocket => {
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat?token=${token}`
  return new WebSocket(wsUrl)
}
