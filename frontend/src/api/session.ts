import http from '@/utils/http'
import type { ApiResponse } from '@/types'

export interface Session {
  id: string
  visitor_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export const sessionApi = {
  /** 创建新会话 */
  create(visitor_id: string, title = '新会话'): Promise<{ data: ApiResponse<Session> }> {
    return http.post('/chat/sessions/', { visitor_id, title })
  },

  /** 获取会话列表 */
  list(visitor_id: string): Promise<{ data: ApiResponse<Session[]> }> {
    return http.get('/chat/sessions/', { params: { visitor_id } })
  },

  /** 获取消息历史 */
  getMessages(session_id: string, visitor_id: string): Promise<{ data: ApiResponse<Message[]> }> {
    return http.get(`/chat/sessions/${session_id}/messages`, { params: { visitor_id } })
  },
}
