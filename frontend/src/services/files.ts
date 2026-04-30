import api from './api'
import { FileRecord, FileUploadResponse } from '../types/file'

export const fileApi = {
  uploadFile: (file: File, conversationId?: number) => {
    const formData = new FormData()
    formData.append('file', file)
    if (conversationId) {
      formData.append('conversation_id', String(conversationId))
    }
    return api.post<FileUploadResponse>('/files/upload', formData)
  },

  listFiles: (conversationId?: number) =>
    api.get<FileRecord[]>('/files', {
      params: conversationId ? { conversation_id: conversationId } : {},
    }),

  deleteFile: (id: number) => api.delete<void>(`/files/${id}`),
}
