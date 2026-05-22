<template>
  <app-layout>
    <div class="chat-layout">
      <!-- 左侧：会话列表 -->
      <aside class="session-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">历史会话</span>
          <el-button
            type="primary"
            size="small"
            :icon="Plus"
            @click="handleNewSession"
            :loading="store.loading"
          >
            新建
          </el-button>
        </div>

        <div class="session-list" v-loading="store.loading">
          <div v-if="store.sessions.length === 0" class="session-empty">
            暂无会话，点击"新建"开始
          </div>
          <div
            v-for="session in store.sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: session.id === store.currentSessionId }"
            @click="handleSwitchSession(session.id)"
          >
            <span class="session-icon">💬</span>
            <span class="session-title">{{ session.title }}</span>
          </div>
        </div>
      </aside>

      <!-- 右侧：聊天区域 -->
      <div class="chat-main">
        <!-- 无会话提示 -->
        <div v-if="!store.currentSessionId" class="no-session">
          <div class="no-session-icon">🧠</div>
          <p>选择或新建一个会话，开始与 NovaMind 对话</p>
          <el-button type="primary" @click="handleNewSession">新建会话</el-button>
        </div>

        <!-- 聊天内容 -->
        <template v-else>
          <!-- 消息列表 -->
          <div ref="msgListRef" class="message-list">
            <div v-if="store.messages.length === 0 && !store.isStreaming" class="empty-hint">
              <div class="empty-icon">🧠</div>
              <p>向 NovaMind 提问，探索企业知识库</p>
            </div>

            <div
              v-for="(msg, idx) in store.messages"
              :key="idx"
              class="message-item"
              :class="msg.role"
            >
              <div class="bubble" v-html="renderMarkdown(msg.content)" />
            </div>

            <!-- 流式占位 -->
            <div v-if="store.isStreaming" class="message-item assistant">
              <div class="bubble" v-html="renderMarkdown(store.streamContent || '...')" />
            </div>
          </div>

          <!-- 输入区 -->
          <div class="input-area">
            <div class="input-controls">
              <el-switch v-model="useRag" active-text="RAG 知识库" inactive-text="纯 AI" />
            </div>
            <div class="input-row">
              <el-input
                v-model="inputText"
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="输入问题，按 Enter 发送，Shift+Enter 换行"
                @keydown.enter.exact.prevent="sendMessage"
                class="chat-input"
                :disabled="store.isStreaming"
              />
              <el-button
                type="primary"
                :loading="store.isStreaming"
                @click="sendMessage"
                class="send-btn"
              >
                发送
              </el-button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/common/AppLayout.vue'
import { streamSessionChat } from '@/api/chat'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const inputText = ref('')
const useRag = ref(true)
const msgListRef = ref<HTMLElement>()

function renderMarkdown(content: string): string {
  return DOMPurify.sanitize(marked(content) as string)
}

async function scrollToBottom() {
  await nextTick()
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  }
}

// ── 初始化 ──────────────────────────────────────────────────────
onMounted(async () => {
  await store.init()
  // 自动选中最近的会话
  if (store.sessions.length > 0 && !store.currentSessionId) {
    await store.switchSession(store.sessions[0].id)
  }
})

// ── 新建会话 ─────────────────────────────────────────────────────
async function handleNewSession() {
  try {
    await store.createSession('新会话')
  } catch {
    ElMessage.error('创建会话失败')
  }
}

// ── 切换会话 ─────────────────────────────────────────────────────
async function handleSwitchSession(sessionId: string) {
  if (store.isStreaming) return
  await store.switchSession(sessionId)
  await scrollToBottom()
}

// ── 发送消息 ─────────────────────────────────────────────────────
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || store.isStreaming || !store.currentSessionId) return

  // 如果没有会话，先创建
  if (!store.currentSessionId) {
    await handleNewSession()
    return
  }

  inputText.value = ''

  // 乐观展示用户消息
  store.addLocalMessage('user', text)
  await scrollToBottom()

  store.isStreaming = true
  store.streamContent = ''

  // 占位 assistant 消息
  store.addLocalMessage('assistant', '')

  try {
    await streamSessionChat(
      {
        visitor_id: store.visitorId,
        session_id: store.currentSessionId,
        message: text,
        use_rag: useRag.value,
      },
      async (chunk) => {
        store.streamContent += chunk
        // 同步更新本地最后一条 assistant 消息（实时展示）
        const last = store.messages[store.messages.length - 1]
        if (last?.role === 'assistant') last.content += chunk
        await scrollToBottom()
      },
      (_name, _result) => {},
      async () => {
        store.isStreaming = false
        store.streamContent = ''
        store.touchSession(store.currentSessionId!)
        await scrollToBottom()
      },
    )
  } catch (e) {
    store.isStreaming = false
    store.streamContent = ''
    ElMessage.error('对话请求失败，请重试')
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: #0f172a;
}

/* ── 侧边栏 ── */
.session-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #1e293b;
  background: #0a1628;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 12px;
  border-bottom: 1px solid #1e293b;
}

.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.05em;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.session-empty {
  padding: 20px 16px;
  color: #475569;
  font-size: 13px;
  text-align: center;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  border-radius: 0;
  transition: background 0.15s;
  color: #94a3b8;
  font-size: 13px;
  border-left: 3px solid transparent;
}

.session-item:hover {
  background: #1e293b;
  color: #e2e8f0;
}

.session-item.active {
  background: #1e293b;
  color: #6366f1;
  border-left-color: #6366f1;
}

.session-icon { flex-shrink: 0; font-size: 14px; }

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 主内容区 ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.no-session {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #475569;
  gap: 16px;
}

.no-session-icon { font-size: 48px; }

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-hint {
  text-align: center;
  color: #475569;
  margin-top: 80px;
}

.empty-icon { font-size: 48px; margin-bottom: 12px; }
.message-item { display: flex; }
.message-item.user { justify-content: flex-end; }
.message-item.assistant { justify-content: flex-start; }

.bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
}

.user .bubble {
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff;
}

.assistant .bubble {
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
}

/* ── 输入区 ── */
.input-area {
  border-top: 1px solid #1e293b;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-controls { display: flex; align-items: center; }
.input-row { display: flex; gap: 12px; align-items: flex-end; }
.chat-input { flex: 1; }
.send-btn { height: 40px; min-width: 80px; }
</style>
