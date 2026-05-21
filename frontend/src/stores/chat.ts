import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)

  function addMessage(message: ChatMessage) {
    messages.value.push(message)
  }

  function appendToLastAssistant(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += content
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return { messages, isStreaming, addMessage, appendToLastAssistant, clearMessages }
})
