import type { ChatRequest } from '@/types'

// 与 http.ts 保持一致，使用同一个 baseURL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

/**
 * 发起 SSE 流式 Chat 请求
 * @param request 请求参数
 * @param onChunk 每次接收到内容时的回调
 * @param onToolCall Tool 调用结果回调
 * @param onDone 完成回调
 */
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

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value, { stream: true })
    const lines = text.split('\n')
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
        // ignore parse errors
      }
    }
  }
  onDone()
}
