<template>
  <div class="app-container">
    <!-- Mobile Sidebar Toggle -->
    <button class="mobile-sidebar-toggle" @click="toggleMobileSidebar" aria-label="Toggle Sidebar">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="4" x2="20" y1="12" y2="12"></line>
        <line x1="4" x2="20" y1="6" y2="6"></line>
        <line x1="4" x2="20" y1="18" y2="18"></line>
      </svg>
    </button>

    <!-- Sidebar component -->
    <Sidebar 
      :sessions="sessions" 
      :current-session-id="currentSessionId" 
      :is-mobile-open="isMobileSidebarOpen"
      @select-session="selectSession"
      @create-session="createNewSession"
      @delete-session="deleteSession"
      @close-mobile="isMobileSidebarOpen = false"
    />

    <!-- Main Content Area -->
    <main class="main-content">
      <header class="app-header glass-panel">
        <div class="header-left">
          <h1 class="gradient-text">NexusAI</h1>
          <span class="api-status" :class="{ connected: apiConnected }">
            <span class="status-dot"></span>
            {{ apiConnected ? '在线' : '离线' }}
          </span>
        </div>
        
        <div class="header-actions">
          <button class="header-btn" @click="showSettings = true" title="模型设置">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <span>模型参数</span>
          </button>
        </div>
      </header>

      <!-- Chat Window component -->
      <ChatWindow 
        v-if="currentSession"
        :session="currentSession"
        :settings="settings"
        @update-messages="updateSessionMessages"
        @update-title="updateSessionTitle"
      />
    </main>

    <!-- Overlay settings drawer/modal -->
    <Settings 
      v-if="showSettings" 
      :settings="settings"
      @close="showSettings = false"
      @update-settings="saveSettings"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatWindow from './components/ChatWindow.vue'
import Settings from './components/Settings.vue'

// Session Management State
const sessions = ref([])
const currentSessionId = ref(null)
const isMobileSidebarOpen = ref(false)
const showSettings = ref(false)
const apiConnected = ref(false)

// Config Settings with default values matching backend/04.py
const settings = ref({
  temperature: 1.0,
  systemPrompt: '你是Python专家',
  maxTokens: 2048
})

// Current Session computations
const currentSession = computed(() => {
  return sessions.value.find(s => s.id === currentSessionId.value) || null
})

// Lifecycle: Load sessions and settings from LocalStorage
onMounted(async () => {
  // Load settings
  const savedSettings = localStorage.getItem('nexus_settings')
  if (savedSettings) {
    try {
      settings.value = { ...settings.value, ...JSON.parse(savedSettings) }
    } catch (e) {
      console.error("Failed to parse settings", e)
    }
  }

  // Load chat sessions
  const savedSessions = localStorage.getItem('nexus_sessions')
  if (savedSessions) {
    try {
      sessions.value = JSON.parse(savedSessions)
    } catch (e) {
      console.error("Failed to parse sessions", e)
    }
  }

  // If no sessions, create the initial one
  if (sessions.value.length === 0) {
    createNewSession()
  } else {
    currentSessionId.value = sessions.value[0].id
  }

  // Check API health
  checkApiHealth()
})

// Watch sessions and save to localStorage
watch(sessions, (newSessions) => {
  localStorage.setItem('nexus_sessions', JSON.stringify(newSessions))
}, { deep: true })

// API Health Check function
async function checkApiHealth() {
  try {
    const res = await fetch('/api/health')
    if (res.ok) {
      const data = await res.json()
      apiConnected.value = data.status === 'healthy'
    } else {
      apiConnected.value = false
    }
  } catch (e) {
    apiConnected.value = false
  }
}

// Toggle mobile sidebar view
function toggleMobileSidebar() {
  isMobileSidebarOpen.value = !isMobileSidebarOpen.value
}

// Select a session
function selectSession(id) {
  currentSessionId.value = id
  isMobileSidebarOpen.value = false
}

// Create a new chat session
function createNewSession() {
  const newSession = {
    id: `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    title: '新对话',
    messages: [],
    createdAt: Date.now()
  }
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  isMobileSidebarOpen.value = false
}

// Delete a session
function deleteSession(id) {
  const index = sessions.value.findIndex(s => s.id === id)
  if (index !== -1) {
    sessions.value.splice(index, 1)
    
    // If we deleted the active session, select another one
    if (currentSessionId.value === id) {
      if (sessions.value.length > 0) {
        currentSessionId.value = sessions.value[0].id
      } else {
        createNewSession()
      }
    }
  }
}

// Update messages in current session
function updateSessionMessages(messages) {
  if (currentSession.value) {
    currentSession.value.messages = messages
  }
}

// Update title in current session (e.g. auto-title based on first message)
function updateSessionTitle({ id, title }) {
  const session = sessions.value.find(s => s.id === id)
  if (session && session.title === '新对话') {
    session.title = title.substring(0, 15) + (title.length > 15 ? '...' : '')
  }
}

// Save model parameter settings
function saveSettings(newSettings) {
  settings.value = { ...newSettings }
  localStorage.setItem('nexus_settings', JSON.stringify(settings.value))
  showSettings.value = false
}
</script>

<style scoped>
/* App Layout Styling */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: relative;
  background: var(--gradient-dark);
  overflow: hidden;
}

.app-header {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-color);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.api-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
  transition: var(--transition-normal);
}

.api-status.connected {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.header-btn {
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.header-btn:hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.15);
}

/* Mobile Sidebar Toggle styling */
.mobile-sidebar-toggle {
  display: none;
  position: absolute;
  top: 22px;
  left: 20px;
  z-index: 100;
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px;
  border-radius: var(--radius-sm);
}

@media (max-width: 768px) {
  .mobile-sidebar-toggle {
    display: block;
  }
  
  .app-header {
    padding-left: 64px; /* Space for toggle button */
  }
  
  .header-btn span {
    display: none; /* Hide button text on mobile */
  }
}
</style>
