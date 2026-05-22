import type { ChatRequest } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

/** 原有接口：无会话版流式对话（兼容保留） */
export async function streamChat(
  request: ChatRequest,
  onChunk: (content: string) => void,
  onToolCall: (name: string, result: unknown) => void,
  onDone: () => void,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok || !response.body) {
    throw new Error(`Chat 请求失败: ${response.status}`)
  }

  await _readSSE(response.body, onChunk, onToolCall, onDone)
}

/** 新接口：基于 session 的流式对话 */
export async function streamSessionChat(
  params: {
    visitor_id: string
    session_id: string
    message: string
    use_rag?: boolean
    workspace_id?: string
  },
  onChunk: (content: string) => void,
  onToolCall: (name: string, result: unknown) => void,
  onDone: () => void,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!response.ok || !response.body) {
    const err = await response.text()
    throw new Error(`Chat 请求失败: ${response.status} ${err}`)
  }

  await _readSSE(response.body, onChunk, onToolCall, onDone)
}

/** SSE 流读取公共逻辑 */
async function _readSSE(
  body: ReadableStream<Uint8Array>,
  onChunk: (content: string) => void,
  onToolCall: (name: string, result: unknown) => void,
  onDone: () => void,
): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (payload === '[DONE]') {
        onDone()
        return
      }
      try {
        const data = JSON.parse(payload)
        if (data.content) onChunk(data.content)
        if (data.tool_call) onToolCall(data.tool_call, data.result)
      } catch {
        // ignore
      }
    }
  }
  onDone()
}
