// ── Chat Types ────────────────────────────────────────────────────

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

export interface ChatMessage {
  role: MessageRole
  content: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  workspace_id?: string
  stream?: boolean
  use_rag?: boolean
}

export interface ToolCallResult {
  tool_call: string
  result: unknown
}

// ── File Types ────────────────────────────────────────────────────

export type FileStatus = 'pending' | 'processing' | 'done' | 'failed'

export interface FileItem {
  id: string
  file_name: string
  file_size: number
  status: FileStatus
  created_at: string
}

export interface FileUploadResponse {
  id: string
  file_name: string
  file_hash: string
  status: FileStatus
  created_at: string
}

// ── API Response ──────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}
