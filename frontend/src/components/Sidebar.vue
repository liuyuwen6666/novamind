<template>
  <div>
    <!-- Mobile Backdrop Overlay -->
    <div 
      v-if="isMobileOpen" 
      class="sidebar-backdrop" 
      @click="$emit('close-mobile')"
    ></div>

    <!-- Sidebar Container -->
    <aside class="sidebar glass-panel" :class="{ 'mobile-open': isMobileOpen }">
      <div class="sidebar-header">
        <div class="logo-area">
          <div class="logo-box">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="url(#logoGrad)" stroke-width="2.5">
              <defs>
                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#6366f1" />
                  <stop offset="100%" stop-color="#a855f7" />
                </linearGradient>
              </defs>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
            </svg>
          </div>
          <div class="logo-text">
            <h2>NexusAI</h2>
            <span>v1.0.0</span>
          </div>
        </div>
        <button class="mobile-close-btn" @click="$emit('close-mobile')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" x2="6" y1="6" y2="18"></line>
            <line x1="6" x2="18" y1="6" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="action-section">
        <button class="new-chat-btn neon-btn" @click="$emit('create-session')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" x2="12" y1="5" y2="19"></line>
            <line x1="5" x2="19" y1="12" y2="12"></line>
          </svg>
          <span>新建对话</span>
        </button>
      </div>

      <!-- History List -->
      <div class="history-section">
        <div class="section-label">对话历史</div>
        <div class="session-list" v-if="sessions.length > 0">
          <div 
            v-for="session in sessions" 
            :key="session.id" 
            class="session-item"
            :class="{ active: session.id === currentSessionId }"
            @click="$emit('select-session', session.id)"
          >
            <!-- Chat bubble icon -->
            <svg class="item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            
            <span class="session-title" :title="session.title">{{ session.title }}</span>
            
            <!-- Delete button -->
            <button 
              class="delete-btn" 
              @click.stop="$emit('delete-session', session.id)"
              title="删除对话"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
        
        <div class="empty-state" v-else>
          暂无历史对话
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="user-profile">
          <div class="avatar">U</div>
          <div class="info">
            <div class="username">普通用户</div>
            <div class="role">本地访客</div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
defineProps({
  sessions: {
    type: Array,
    required: true
  },
  currentSessionId: {
    type: String,
    required: true
  },
  isMobileOpen: {
    type: Boolean,
    default: false
  }
})

defineEmits([
  'select-session', 
  'create-session', 
  'delete-session', 
  'close-mobile'
])
</script>

<style scoped>
.sidebar {
  width: 280px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  z-index: 50;
  transition: var(--transition-normal);
}

.sidebar-header {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-color);
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-box {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text h2 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.2px;
}

.logo-text span {
  font-size: 0.65rem;
  color: var(--text-muted);
  display: block;
}

.mobile-close-btn {
  display: none;
  color: var(--text-secondary);
  padding: 4px;
}

.action-section {
  padding: 20px;
}

.new-chat-btn {
  width: 100%;
  padding: 12px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
}

.history-section {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  padding: 10px 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 10px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  position: relative;
  border: 1px solid transparent;
}

.session-item:hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
  border-color: rgba(255, 255, 255, 0.03);
}

.session-item.active {
  background: rgba(99, 102, 241, 0.08);
  color: var(--text-primary);
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: inset 0 0 12px rgba(99, 102, 241, 0.05);
}

.session-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 3px;
  border-radius: var(--radius-full);
  background: var(--gradient-neon);
}

.item-icon {
  flex-shrink: 0;
  opacity: 0.7;
}

.session-item.active .item-icon {
  color: var(--accent-primary);
  opacity: 1;
}

.session-title {
  flex: 1;
  font-size: 0.85rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  padding: 4px;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
  opacity: 0;
  transition: var(--transition-fast);
}

.session-item:hover .delete-btn {
  opacity: 0.8;
}

.delete-btn:hover {
  color: #f87171 !important;
  background: rgba(239, 68, 68, 0.1);
  opacity: 1 !important;
}

.empty-state {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-align: center;
  padding: 30px 10px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  background: rgba(8, 9, 13, 0.4);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--gradient-neon);
  color: white;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', sans-serif;
  box-shadow: var(--shadow-sm);
}

.info .username {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.info .role {
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* Mobile Responsive Sidebar classes */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    box-shadow: 0 0 40px rgba(0,0,0,0.8);
    background: var(--bg-secondary);
  }
  
  .sidebar.mobile-open {
    transform: translateX(0);
  }
  
  .mobile-close-btn {
    display: block;
  }
  
  .sidebar-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 45;
    animation: fadeIn 0.2s ease-out;
  }
}
</style>
