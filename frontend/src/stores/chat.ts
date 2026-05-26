import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sessionApi } from '@/api/session'
import type { Session, Message } from '@/api/session'

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // 兼容非安全上下文（HTTP）或旧版浏览器的降级方案
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// ── visitor_id 管理（localStorage 持久化）──────────────────────
function getOrCreateVisitorId(): string {
  const key = 'novamind_visitor_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = generateUUID()
    localStorage.setItem(key, id)
  }
  return id
}

export const useChatStore = defineStore('chat', () => {
  // ── 基础状态 ──────────────────────────────────────────────────
  const visitorId = ref<string>(getOrCreateVisitorId())
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const isStreaming = ref(false)
  const streamContent = ref('')
  const loading = ref(false)

  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value) ?? null
  )

  // ── 初始化：加载会话列表 ──────────────────────────────────────
  async function init() {
    await loadSessions()
  }

  async function loadSessions() {
    try {
      loading.value = true
      const res = await sessionApi.list(visitorId.value)
      sessions.value = (res.data as unknown as Session[]) ?? []
    } catch (e) {
      console.error('加载会话失败', e)
    } finally {
      loading.value = false
    }
  }

  // ── 创建新会话 ────────────────────────────────────────────────
  async function createSession(title = '新会话'): Promise<Session> {
    const res = await sessionApi.create(visitorId.value, title)
    const session = res.data as unknown as Session
    sessions.value.unshift(session)
    await switchSession(session.id)
    return session
  }

  // ── 切换会话 ──────────────────────────────────────────────────
  async function switchSession(sessionId: string) {
    if (currentSessionId.value === sessionId) return
    currentSessionId.value = sessionId
    messages.value = []
    streamContent.value = ''
    await loadMessages(sessionId)
  }

  // ── 加载消息历史 ──────────────────────────────────────────────
  async function loadMessages(sessionId: string) {
    try {
      const res = await sessionApi.getMessages(sessionId, visitorId.value)
      messages.value = (res.data as unknown as Message[]) ?? []
    } catch (e) {
      console.error('加载消息历史失败', e)
    }
  }

  // ── 追加本地消息（流式结束后调用）────────────────────────────
  function addLocalMessage(role: 'user' | 'assistant', content: string) {
    const fake: Message = {
      id: generateUUID(),
      session_id: currentSessionId.value!,
      role,
      content,
      created_at: new Date().toISOString(),
    }
    messages.value.push(fake)
  }

  // ── 追加到最后一条 assistant 消息（流式块）───────────────────
  function appendToLastAssistant(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += content
    }
  }

  // ── 更新会话的 updated_at（乐观更新，让侧边栏重排）──────────
  function touchSession(sessionId: string) {
    const s = sessions.value.find(x => x.id === sessionId)
    if (s) {
      s.updated_at = new Date().toISOString()
      // 重排到顶部
      sessions.value = [s, ...sessions.value.filter(x => x.id !== sessionId)]
    }
  }

  return {
    visitorId,
    sessions,
    currentSessionId,
    currentSession,
    messages,
    isStreaming,
    streamContent,
    loading,
    init,
    loadSessions,
    createSession,
    switchSession,
    loadMessages,
    addLocalMessage,
    appendToLastAssistant,
    touchSession,
  }
})
