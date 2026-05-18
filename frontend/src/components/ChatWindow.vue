<template>
  <div class="chat-container">
    <!-- Messages Scroll Area -->
    <div class="messages-area" ref="messagesAreaRef" @scroll="handleScroll">
      
      <!-- Welcome/Empty State -->
      <div v-if="session.messages.length === 0" class="welcome-container animate-fade-in">
        <div class="welcome-hero">
          <div class="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="url(#heroGrad)" stroke-width="1.5">
              <defs>
                <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#06b6d4" />
                  <stop offset="100%" stop-color="#6366f1" />
                </linearGradient>
              </defs>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <h2>有什么我可以帮您的？</h2>
          <p>基于 NexusAI 大语言模型构建，支持实时流式回答、系统角色自定义和参数微调。</p>
        </div>

        <div class="suggestions-grid">
          <div 
            v-for="(suggestion, idx) in suggestions" 
            :key="idx" 
            class="suggestion-card glass-panel"
            @click="useSuggestion(suggestion.prompt)"
          >
            <div class="card-icon" :style="{ color: suggestion.color }">
              <component :is="suggestion.icon" />
            </div>
            <h4>{{ suggestion.title }}</h4>
            <p>{{ suggestion.prompt }}</p>
          </div>
        </div>
      </div>

      <!-- Dialogue Bubbles -->
      <div v-else class="bubbles-wrapper">
        <div 
          v-for="(msg, index) in session.messages" 
          :key="index" 
          class="bubble-row" 
          :class="msg.role"
        >
          <!-- Avatar -->
          <div class="bubble-avatar" :class="msg.role">
            <span v-if="msg.role === 'user'">U</span>
            <span v-else>AI</span>
          </div>

          <!-- Content Frame -->
          <div class="bubble-content-wrapper">
            <div class="bubble-meta">
              <span class="sender-name">{{ msg.role === 'user' ? '您' : 'NexusAI' }}</span>
            </div>
            
            <div 
              class="bubble-text" 
              :class="{ 'glass-panel': msg.role === 'assistant' }"
              v-html="msg.role === 'user' ? escapeHTML(msg.content) : renderMarkdown(msg.content)"
            ></div>

            <!-- Bubble Actions (Assistant Only) -->
            <div v-if="msg.role === 'assistant' && msg.content" class="bubble-actions">
              <button 
                class="action-icon-btn" 
                @click="copyToClipboard(msg.content, index)" 
                :title="copyState[index] ? '已复制' : '复制回答'"
              >
                <svg v-if="!copyState[index]" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <svg v-else class="success-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>{{ copyState[index] ? '已复制' : '复制' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- AI Streaming Loader -->
        <div v-if="isStreaming && currentAssistantMessage === ''" class="bubble-row assistant">
          <div class="bubble-avatar assistant">AI</div>
          <div class="bubble-content-wrapper">
            <div class="bubble-meta">
              <span class="sender-name">NexusAI</span>
            </div>
            <div class="bubble-text glass-panel loader-bubble">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Auto-scroll anchor -->
      <div ref="scrollAnchorRef"></div>
    </div>

    <!-- Scroll Down indicator -->
    <button v-if="showScrollDown" class="scroll-down-btn" @click="scrollToBottom">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <line x1="12" x2="12" y1="5" y2="19"></line>
        <polyline points="19 12 12 19 5 12"></polyline>
      </svg>
    </button>

    <!-- Bottom Input Controls -->
    <div class="input-panel-container glass-panel">
      <div class="input-actions-bar">
        <div class="model-badge">
          <span class="pulse-indicator"></span>
          longcat-flash-chat
        </div>
        <div class="system-badge" :title="settings.systemPrompt">
          角色: {{ settings.systemPrompt.substring(0, 10) }}{{ settings.systemPrompt.length > 10 ? '...' : '' }}
        </div>
      </div>
      
      <div class="input-form">
        <textarea 
          ref="textareaRef"
          v-model="inputMessage" 
          placeholder="问问我任何关于 Python、算法或者网页开发的问题... (Enter 发送，Shift+Enter 换行)"
          rows="1"
          @keydown="handleKeydown"
          :disabled="isStreaming && currentAssistantMessage === ''"
        ></textarea>
        
        <div class="button-container">
          <!-- Cancel/Stop stream button -->
          <button 
            v-if="isStreaming" 
            type="button" 
            class="stop-btn" 
            @click="stopGeneration"
            title="停止生成"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>
            </svg>
            <span>停止</span>
          </button>
          
          <!-- Send button -->
          <button 
            v-else
            type="button" 
            class="send-btn neon-btn" 
            @click="sendMessage"
            :disabled="!inputMessage.trim()"
            title="发送消息"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" x2="11" y1="2" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <span>发送</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick, h } from 'vue'
import { marked } from 'marked'

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true
})

const props = defineProps({
  session: {
    type: Object,
    required: true
  },
  settings: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update-messages', 'update-title'])

// UI States
const inputMessage = ref('')
const isStreaming = ref(false)
const currentAssistantMessage = ref('')
const showScrollDown = ref(false)
const copyState = ref({})

// DOM References
const messagesAreaRef = ref(null)
const scrollAnchorRef = ref(null)
const textareaRef = ref(null)

// Abort Controller for Stream Cancellation
let abortController = null
let isUserScrolling = false

// Quick Suggestion Cards configurations
const suggestions = [
  {
    title: 'Python 贪吃蛇',
    prompt: '用 Python 编写一个可以在终端运行或带有简易界面的经典贪吃蛇小游戏。',
    color: '#06b6d4',
    icon: {
      render() {
        return h('svg', { width: '20', height: '20', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
          h('path', { d: 'M12 2L2 7l10 5 10-5-10-5z' }),
          h('path', { d: 'M2 17l10 5 10-5' }),
          h('path', { d: 'M2 12l10 5 10-5' })
        ])
      }
    }
  },
  {
    title: '量子纠缠浅析',
    prompt: '请用一个 10 岁小孩能听懂的通俗语言，向我解释什么是“量子纠缠”？',
    color: '#a855f7',
    icon: {
      render() {
        return h('svg', { width: '20', height: '20', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
          h('circle', { cx: '12', cy: '12', r: '10' }),
          h('line', { x1: '2', y1: '12', x2: '22', y2: '12' }),
          h('path', { d: 'M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z' })
        ])
      }
    }
  },
  {
    title: 'CSS 磨砂玻璃效果',
    prompt: '如何用 CSS 实现极致优雅的磨砂玻璃透镜效果 (Glassmorphism UI)？给出代码和解释。',
    color: '#3b82f6',
    icon: {
      render() {
        return h('svg', { width: '20', height: '20', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
          h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2', ry: '2' }),
          h('line', { x1: '9', y1: '3', x2: '9', y2: '21' }),
          h('line', { x1: '15', y1: '3', x2: '15', y2: '21' }),
          h('line', { x1: '3', y1: '9', x2: '21', y2: '9' }),
          h('line', { x1: '3', y1: '15', x2: '21', y2: '15' })
        ])
      }
    }
  }
]

// Handle Suggestion Click
function useSuggestion(prompt) {
  inputMessage.value = prompt
  nextTick(() => {
    sendMessage()
  });
}

// Watch inputs and auto-grow textarea height
watch(inputMessage, () => {
  nextTick(adjustTextareaHeight)
})

// Auto-grow textarea functionality
function adjustTextareaHeight() {
  const ta = textareaRef.value
  if (!ta) return
  ta.style.height = 'auto'
  const newHeight = Math.min(ta.scrollHeight, 160)
  ta.style.height = `${newHeight}px`
}

// Watch active session changing to focus input & scroll
watch(() => props.session.id, () => {
  stopGeneration()
  inputMessage.value = ''
  nextTick(() => {
    scrollToBottom()
    adjustTextareaHeight()
    if (textareaRef.value) textareaRef.value.focus()
  })
})

onMounted(() => {
  scrollToBottom()
  if (textareaRef.value) textareaRef.value.focus()
})

// Escape HTML for User bubbles to prevent XSS
function escapeHTML(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/\n/g, '<br />')
}

// Compile Markdown using marked
function renderMarkdown(text) {
  if (!text) return ''
  try {
    return marked.parse(text)
  } catch (e) {
    return text
  }
}

// Scroll Handling to show/hide "Scroll to Bottom" badge
function handleScroll() {
  const area = messagesAreaRef.value
  if (!area) return
  
  // Show scroll-down button if user scrolled up significantly
  const diff = area.scrollHeight - area.scrollTop - area.clientHeight
  showScrollDown.value = diff > 300
  
  // Check if user is scrolling up manually
  isUserScrolling = diff > 40
}

// Scroll to bottom helper
function scrollToBottom() {
  nextTick(() => {
    const area = messagesAreaRef.value
    if (area) {
      area.scrollTop = area.scrollHeight
    }
    showScrollDown.value = false
    isUserScrolling = false
  })
}

// Key event listener for textarea
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// Copy bubble to clipboard
async function copyToClipboard(text, idx) {
  try {
    await navigator.clipboard.writeText(text)
    copyState.value[idx] = true
    setTimeout(() => {
      copyState.value[idx] = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy', err)
  }
}

// Send user prompt & stream response
async function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text || isStreaming.value) return

  // Create user message
  const userMsg = { role: 'user', content: text }
  const updatedMessages = [...props.session.messages, userMsg]
  
  emit('update-messages', updatedMessages)
  inputMessage.value = ''
  isStreaming.value = true
  currentAssistantMessage.value = ''
  
  // Auto update title if this is the first user query
  if (props.session.messages.length === 1) {
    emit('update-title', { id: props.session.id, title: text })
  }

  // Create initial empty AI response container
  const assistantMsg = { role: 'assistant', content: '' }
  const streamMessages = [...updatedMessages, assistantMsg]
  emit('update-messages', streamMessages)
  
  scrollToBottom()

  // Setup abort controller for cancel feature
  abortController = new AbortController()
  
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: updatedMessages,
        temperature: props.settings.temperature,
        system_prompt: props.settings.systemPrompt
      }),
      signal: abortController.signal
    })

    if (!response.ok) {
      throw new Error(`网络请求错误 (HTTP ${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      
      // Save partial line
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6)
          try {
            const dataObj = JSON.parse(dataStr)
            
            if (dataObj.content) {
              assistantMsg.content += dataObj.content
              currentAssistantMessage.value = assistantMsg.content
              
              // Only auto scroll down if the user isn't scrolling up to inspect history!
              if (!isUserScrolling) {
                scrollToBottom()
              }
            }
            if (dataObj.done) {
              break
            }
            if (dataObj.error) {
              assistantMsg.content += `\n\n**API 错误:** ${dataObj.error}`
              currentAssistantMessage.value = assistantMsg.content
              break
            }
          } catch (e) {
            console.error('JSON parse error in SSE stream', e)
          }
        }
      }
    }
  } catch (err) {
    // If not aborted manually by user
    if (err.name !== 'AbortError') {
      assistantMsg.content += `\n\n**生成异常:** ${err.message}`
      currentAssistantMessage.value = assistantMsg.content
    }
  } finally {
    isStreaming.value = false
    abortController = null
    scrollToBottom()
  }
}

// Stop current response generation
function stopGeneration() {
  if (abortController) {
    abortController.abort()
    isStreaming.value = false
    abortController = null
  }
}
</script>

<style scoped>
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 70px);
  position: relative;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 30px 24px;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* Empty State / Welcome Screen styling */
.welcome-container {
  max-width: 800px;
  width: 100%;
  margin: auto;
  display: flex;
  flex-direction: column;
  gap: 40px;
  padding: 20px 0;
}

.welcome-hero {
  text-align: center;
}

.welcome-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-lg);
  background: rgba(6, 182, 212, 0.08);
  border: 1px solid rgba(6, 182, 212, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px auto;
  box-shadow: 0 10px 30px rgba(6, 182, 212, 0.1);
}

.welcome-hero h2 {
  font-family: 'Outfit', sans-serif;
  font-size: 2.2rem;
  font-weight: 800;
  margin-bottom: 12px;
  background: var(--gradient-cyan);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-hero p {
  color: var(--text-secondary);
  font-size: 1rem;
  max-width: 540px;
  margin: 0 auto;
  line-height: 1.6;
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.suggestion-card {
  padding: 20px;
  border-radius: var(--radius-lg);
  cursor: pointer;
  background: rgba(15, 17, 26, 0.4);
}

.suggestion-card:hover {
  background: var(--bg-glass-hover);
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-4px);
  box-shadow: 0 10px 24px rgba(0,0,0,0.5), 0 0 15px rgba(99, 102, 241, 0.1);
}

.card-icon {
  margin-bottom: 12px;
}

.suggestion-card h4 {
  font-family: 'Outfit', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: 6px;
}

.suggestion-card p {
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.4;
}

/* Bubbles Wrapper styling */
.bubbles-wrapper {
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.bubble-row {
  display: flex;
  gap: 16px;
  width: 100%;
}

.bubble-row.user {
  flex-direction: row-reverse;
}

.bubble-avatar {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
  font-family: 'Outfit', sans-serif;
}

.bubble-avatar.user {
  background: var(--gradient-neon);
  color: white;
}

.bubble-avatar.assistant {
  background: var(--gradient-cyan);
  color: white;
}

.bubble-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: calc(100% - 100px);
}

.bubble-row.user .bubble-content-wrapper {
  align-items: flex-end;
}

.bubble-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 500;
}

.bubble-text {
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  font-size: 0.95rem;
  line-height: 1.6;
  word-break: break-word;
}

.bubble-row.user .bubble-text {
  background: var(--gradient-neon);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
}

.bubble-row.assistant .bubble-text {
  border-bottom-left-radius: 4px;
  color: var(--text-primary);
  background: var(--bg-glass);
}

/* Assistant markdown styling adjustments */
:deep(.bubble-text) p {
  margin-bottom: 10px;
}

:deep(.bubble-text) p:last-child {
  margin-bottom: 0;
}

:deep(.bubble-text) ul, :deep(.bubble-text) ol {
  margin-left: 20px;
  margin-bottom: 10px;
}

:deep(.bubble-text) li {
  margin-bottom: 4px;
}

:deep(.bubble-text) code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
  border: 1px solid rgba(255,255,255,0.05);
}

:deep(.bubble-text) pre code {
  background: transparent;
  padding: 0;
  border-radius: 0;
  border: none;
  font-size: 0.9rem;
}

/* Loader dots bubble */
.loader-bubble {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 16px 24px;
}

.loader-bubble .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--accent-tertiary);
  animation: bounce 1.4s infinite ease-in-out both;
}

.loader-bubble .dot:nth-child(1) { animation-delay: -0.32s; }
.loader-bubble .dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.bubble-actions {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}

.action-icon-btn {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: transparent;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.action-icon-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.action-icon-btn svg {
  margin-right: 4px;
}

/* Scroll down floating icon */
.scroll-down-btn {
  position: absolute;
  bottom: 120px;
  right: 40px;
  background: var(--accent-primary);
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
  animation: fadeIn 0.2s ease-out;
}

.scroll-down-btn:hover {
  background: var(--accent-secondary);
  transform: translateY(2px);
}

/* Bottom Input panel details */
.input-panel-container {
  margin: 0 24px 24px 24px;
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  max-width: 900px;
  width: calc(100% - 48px);
  align-self: center;
  background: rgba(15, 17, 26, 0.6);
  border: 1px solid var(--border-color);
}

.input-actions-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 0.7rem;
  font-weight: 600;
}

.model-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(6, 182, 212, 0.1);
  color: var(--accent-tertiary);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulseGlow 1.8s infinite;
}

.system-badge {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
}

.input-form {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

textarea {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 0.92rem;
  line-height: 1.5;
  max-height: 160px;
  min-height: 24px;
  resize: none;
  padding: 4px 0;
}

textarea::placeholder {
  color: var(--text-muted);
}

.button-container {
  display: flex;
  gap: 8px;
}

.send-btn, .stop-btn {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  height: 38px;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.stop-btn {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.stop-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
}

@media (max-width: 768px) {
  .messages-area {
    padding: 20px 16px;
  }
  
  .input-panel-container {
    margin: 0 12px 12px 12px;
    width: calc(100% - 24px);
  }
  
  .send-btn span, .stop-btn span {
    display: none; /* Icon-only on mobile */
  }
  
  .send-btn, .stop-btn {
    width: 38px;
    padding: 0;
    justify-content: center;
  }
  
  .scroll-down-btn {
    right: 20px;
  }
}
</style>
