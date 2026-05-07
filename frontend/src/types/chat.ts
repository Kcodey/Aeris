export interface Message {
  id: number;
  conversation_id: number;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | null;
  tool_calls?: any[];
  created_at: string;
  // 前端扩展：关联的文件记录（用于图片展示）
  file_records?: any[];
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
  last_message_preview?: string | null;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: number;
}

export interface ChatResponse {
  message: Message;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
  tool_calls: any[];
}

export interface StreamingChunk {
  type: 'content' | 'tool_call' | 'done' | 'error';
  content?: string;
  tool_call?: any;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
  error?: string;
}
