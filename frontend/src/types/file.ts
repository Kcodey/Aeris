export interface FileRecord {
  id: number
  original_name: string
  mime_type: string
  size_bytes: number
  size_display: string
  is_image?: boolean
  created_at: string
}

export type FileUploadResponse = FileRecord
