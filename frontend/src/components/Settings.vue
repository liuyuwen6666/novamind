<template>
  <div class="modal-backdrop animate-fade-in" @click.self="$emit('close')">
    <div class="settings-modal glass-panel animate-slide-up">
      <header class="modal-header">
        <div class="title-wrapper">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="url(#modalGrad)" stroke-width="2">
            <defs>
              <linearGradient id="modalGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#6366f1" />
                <stop offset="100%" stop-color="#a855f7" />
              </linearGradient>
            </defs>
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <h3>模型参数配置</h3>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" x2="6" y1="6" y2="18"></line>
            <line x1="6" x2="18" y1="6" y2="18"></line>
          </svg>
        </button>
      </header>

      <div class="modal-body">
        <!-- System Prompt Area -->
        <div class="setting-group">
          <label class="setting-label">
            <span>系统预设角色提示词 (System Prompt)</span>
            <span class="badge">指令</span>
          </label>
          <div class="textarea-wrapper">
            <textarea 
              v-model="localSettings.systemPrompt" 
              placeholder="例如：你是Python专家，只使用精简的代码回答..."
              rows="4"
            ></textarea>
          </div>
          <p class="setting-desc">用来指导 AI 的身份、语气、限制或行为规范。这会在会话的初始轮次注入。</p>
        </div>

        <!-- Temperature Slider -->
        <div class="setting-group">
          <div class="label-row">
            <label class="setting-label">随机性温度 (Temperature)</label>
            <span class="value-display">{{ localSettings.temperature.toFixed(1) }}</span>
          </div>
          <div class="slider-wrapper">
            <input 
              type="range" 
              v-model.number="localSettings.temperature" 
              min="0" 
              max="2" 
              step="0.1" 
              class="range-slider"
            />
          </div>
          <div class="slider-ticks">
            <span>精确/事实 (0.0)</span>
            <span>平衡 (1.0)</span>
            <span>创造性 (2.0)</span>
          </div>
          <p class="setting-desc">值越高，生成的回答越随机和富有创意；值越低，生成的回答越保守和精炼。</p>
        </div>

        <!-- Max Tokens Slider -->
        <div class="setting-group">
          <div class="label-row">
            <label class="setting-label">最大生成长度 (Max Tokens)</label>
            <span class="value-display">{{ localSettings.maxTokens }}</span>
          </div>
          <div class="slider-wrapper">
            <input 
              type="range" 
              v-model.number="localSettings.maxTokens" 
              min="256" 
              max="4096" 
              step="128" 
              class="range-slider"
            />
          </div>
          <div class="slider-ticks">
            <span>256</span>
            <span>2048</span>
            <span>4096</span>
          </div>
          <p class="setting-desc">限制单次模型回答的上限字数 (Tokens)。较大的回答可能会消耗更多时间和额度。</p>
        </div>
      </div>

      <footer class="modal-footer">
        <button class="cancel-btn" @click="$emit('close')">取消</button>
        <button class="save-btn neon-btn" @click="save">保存设置</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'update-settings'])

const localSettings = ref({
  temperature: 1.0,
  systemPrompt: '',
  maxTokens: 2048
})

onMounted(() => {
  // Make a local reactive copy of current settings to allow cancellation
  localSettings.value = { ...props.settings }
})

function save() {
  emit('update-settings', { ...localSettings.value })
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.settings-modal {
  width: 100%;
  max-width: 540px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7), var(--shadow-glow);
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(15, 17, 26, 0.4);
}

.title-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-wrapper h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
}

.close-btn {
  color: var(--text-secondary);
  padding: 4px;
  border-radius: var(--radius-sm);
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-height: 70vh;
  overflow-y: auto;
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-label .badge {
  font-size: 0.65rem;
  font-weight: 700;
  background: rgba(168, 85, 247, 0.15);
  color: var(--accent-secondary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(168, 85, 247, 0.2);
}

.value-display {
  font-family: 'Outfit', monospace;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--accent-primary);
}

.textarea-wrapper {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px;
  transition: var(--transition-fast);
}

.textarea-wrapper:focus-within {
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.15);
}

textarea {
  width: 100%;
  resize: vertical;
  background: transparent;
  color: var(--text-primary);
  font-size: 0.85rem;
  line-height: 1.5;
}

.range-slider {
  width: 100%;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  appearance: none;
  outline: none;
  cursor: pointer;
}

.range-slider::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--gradient-neon);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
  transition: var(--transition-fast);
}

.range-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.slider-ticks {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.setting-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background: rgba(15, 17, 26, 0.4);
}

.cancel-btn {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
}

.save-btn {
  padding: 10px 24px;
}
</style>
