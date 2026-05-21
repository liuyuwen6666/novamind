<template>
  <app-layout>
    <div class="chat-page">
      <!-- 消息列表 -->
      <div ref="msgListRef" class="message-list">
        <div v-if="messages.length === 0" class="empty-hint">
          <div class="empty-icon">🧠</div>
          <p>向 NovaMind 提问，探索企业知识库</p>
        </div>
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-item"
          :class="msg.role"
        >
          <div class="bubble" v-html="renderMarkdown(msg.content)" />
        </div>
        <!-- 流式占位 -->
        <div v-if="isStreaming && streamContent" class="message-item assistant">
          <div class="bubble" v-html="renderMarkdown(streamContent)" />
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
          />
          <el-button
            type="primary"
            :loading="isStreaming"
            @click="sendMessage"
            class="send-btn"
          >
            发送
          </el-button>
        </div>
      </div>
    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import AppLayout from '@/components/common/AppLayout.vue'
import { streamChat } from '@/api/chat'
import type { ChatMessage } from '@/types'
import { ElMessage } from 'element-plus'

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isStreaming = ref(false)
const streamContent = ref('')
const msgListRef = ref<HTMLElement>()
const useRag = ref(true)

function renderMarkdown(content: string): string {
  return DOMPurify.sanitize(marked(content) as string)
}

async function scrollToBottom() {
  await nextTick()
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  inputText.value = ''
  messages.value.push({ role: 'user', content: text })
  await scrollToBottom()

  isStreaming.value = true
  streamContent.value = ''

  try {
    await streamChat(
      { messages: messages.value, stream: true, use_rag: useRag.value },
      async (chunk) => {
        streamContent.value += chunk
        await scrollToBottom()
      },
      (_name, _result) => {
        // Tool Call 可在此展示
      },
      () => {
        messages.value.push({ role: 'assistant', content: streamContent.value })
        streamContent.value = ''
        isStreaming.value = false
        scrollToBottom()
      },
    )
  } catch (e) {
    isStreaming.value = false
    ElMessage.error('对话请求失败')
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f172a;
}
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
