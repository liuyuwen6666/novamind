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
              <div class="message-content-wrapper">
                <div class="bubble">
                  <template v-if="msg.role === 'assistant' && !msg.content && store.isStreaming && idx === store.messages.length - 1">
                    <div class="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </template>
                  <div v-else class="markdown-body" v-html="renderMarkdown(msg.content || '')" />
                </div>
                <!-- 消息内容下方的辅助工具栏（复制全文） -->
                <div v-if="msg.role === 'assistant' && msg.content" class="message-actions">
                  <el-button
                    link
                    size="small"
                    :icon="DocumentCopy"
                    class="copy-msg-btn"
                    title="复制全文"
                    @click="copyText(msg.content)"
                  >
                    复制全文
                  </el-button>
                </div>
              </div>
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
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { Plus, DocumentCopy } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/common/AppLayout.vue'
import { streamSessionChat } from '@/api/chat'
import { useChatStore } from '@/stores/chat'

// 配置 marked 的代码高亮与渲染包装
marked.use({
  renderer: {
    code(code: string, lang: string | undefined) {
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted = hljs.highlight(code, { language }).value
      return `
        <div class="code-block-wrapper">
          <div class="code-block-header">
            <span class="code-block-lang">${language}</span>
            <button class="copy-code-btn" onclick="window.copyCode(this)">
              <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-bottom;">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span class="btn-text">复制</span>
            </button>
          </div>
          <pre><code class="hljs language-${language}">${highlighted}</code></pre>
        </div>
      `
    }
  }
})

const store = useChatStore()
const inputText = ref('')
const useRag = ref(true)
const msgListRef = ref<HTMLElement>()

function renderMarkdown(content: string): string {
  if (!content) return ''
  return DOMPurify.sanitize(marked.parse(content) as string)
}

async function scrollToBottom() {
  await nextTick()
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  }
}

// ── 复制全文方法 ──────────────────────────────────────────────────
async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败，请重试')
  }
}

// ── 初始化 ──────────────────────────────────────────────────────
onMounted(async () => {
  await store.init()
  // 自动选中最近的会话
  if (store.sessions.length > 0 && !store.currentSessionId) {
    await store.switchSession(store.sessions[0].id)
  }

  // 注册全局代码复制方法
  ;(window as any).copyCode = async (btn: HTMLButtonElement) => {
    const wrapper = btn.closest('.code-block-wrapper')
    if (!wrapper) return
    const codeEl = wrapper.querySelector('code')
    if (!codeEl) return
    const codeText = codeEl.textContent || ''
    
    try {
      await navigator.clipboard.writeText(codeText)
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" width="13" height="13" stroke="#10b981" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-bottom;">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span class="btn-text" style="color: #10b981;">已复制</span>
      `
      setTimeout(() => {
        btn.innerHTML = `
          <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: text-bottom;">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span class="btn-text">复制</span>
        `
      }, 2000)
    } catch {
      ElMessage.error('复制代码失败')
    }
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
    
    // 捕获异常，并对空占位消息填补错误展示
    const last = store.messages[store.messages.length - 1]
    if (last && last.role === 'assistant' && !last.content) {
      last.content = '❌ **请求异常**：未能与服务器建立连接，请重试。'
    }
    
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

/* 对话气泡与操作栏的列布局包裹 */
.message-content-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}

.message-item.user .message-content-wrapper {
  align-items: flex-end;
}

.message-item.assistant .message-content-wrapper {
  align-items: flex-start;
}

.bubble {
  max-width: 100%;
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

/* 消息气泡下方的操作控制栏 */
.message-actions {
  margin-top: 4px;
  display: flex;
  gap: 8px;
  padding-left: 4px;
}

.copy-msg-btn {
  color: #64748b !important;
  font-size: 11px !important;
  padding: 2px 4px !important;
  height: auto !important;
  transition: all 0.15s ease;
}

.copy-msg-btn:hover {
  color: #6366f1 !important;
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

/* ── 动态打字效果 (Typing Indicator) ── */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 20px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #6366f1;
  border-radius: 50%;
  animation: pulse 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* ── Markdown 渲染元素深度美化 ── */
.bubble :deep(p) {
  margin: 0 0 10px 0;
}
.bubble :deep(p:last-child) {
  margin-bottom: 0;
}

.bubble :deep(h1),
.bubble :deep(h2),
.bubble :deep(h3),
.bubble :deep(h4),
.bubble :deep(h5),
.bubble :deep(h6) {
  color: #f8fafc;
  margin: 16px 0 8px 0;
  font-weight: 600;
}

.bubble :deep(h1) { font-size: 1.5em; border-bottom: 1px solid #334155; padding-bottom: 4px; }
.bubble :deep(h2) { font-size: 1.3em; }
.bubble :deep(h3) { font-size: 1.15em; }

/* 工具调用块 (Blockquote) 设计样式 */
.bubble :deep(blockquote) {
  margin: 12px 0;
  padding: 10px 14px;
  background: #0b1329;
  border-left: 4px solid #6366f1;
  border-radius: 4px;
  color: #94a3b8;
}

.bubble :deep(blockquote p) {
  margin-bottom: 6px;
}
.bubble :deep(blockquote p:last-child) {
  margin-bottom: 0;
}
.bubble :deep(blockquote strong) {
  color: #e2e8f0;
}

/* 代码块容器 wrapper */
.bubble :deep(.code-block-wrapper) {
  margin: 14px 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #1e293b;
  background: #090d16;
}

/* 代码块预格式化 pre 部分调整 */
.bubble :deep(.code-block-wrapper pre) {
  margin: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  padding: 12px 16px;
}

/* 代码段工具栏 */
.bubble :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 14px;
  background: #141f36;
  border-bottom: 1px solid #1e293b;
}

.bubble :deep(.code-block-lang) {
  font-size: 11px;
  font-family: 'Fira Code', Consolas, Monaco, monospace;
  color: #64748b;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.bubble :deep(.copy-code-btn) {
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 11.5px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.bubble :deep(.copy-code-btn:hover) {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.06);
}

.bubble :deep(.copy-code-btn svg) {
  flex-shrink: 0;
}

/* 行内代码 */
.bubble :deep(code) {
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
  font-size: 12.5px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  padding: 2px 5px;
  border-radius: 4px;
}

.bubble :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
  font-size: 12.5px;
}

/* 列表 (Lists) */
.bubble :deep(ul),
.bubble :deep(ol) {
  margin: 0 0 10px 0;
  padding-left: 20px;
}
.bubble :deep(li) {
  margin-bottom: 4px;
}

/* 表格 (Table) */
.bubble :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
}

.bubble :deep(th),
.bubble :deep(td) {
  border: 1px solid #334155;
  padding: 8px 12px;
  text-align: left;
}

.bubble :deep(th) {
  background: #1e293b;
  color: #f1f5f9;
  font-weight: 600;
}

.bubble :deep(tr:nth-child(even)) {
  background: #111b27;
}
</style>
