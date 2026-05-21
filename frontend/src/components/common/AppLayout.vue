<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <span class="logo-icon">🧠</span>
        <span class="logo-text">NovaMind</span>
      </div>
      <el-menu :default-active="activeRoute" router class="nav-menu">
        <el-menu-item index="/chat">
          <el-icon><ChatLineRound /></el-icon>
          <span>AI 对话</span>
        </el-menu-item>
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>上传文档</span>
        </el-menu-item>
        <el-menu-item index="/files">
          <el-icon><Files /></el-icon>
          <span>文件管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="main-content">
      <slot />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeRoute = computed(() => route.path)
</script>

<style scoped>
.layout {
  height: 100vh;
}
.sidebar {
  background: #0f172a;
  display: flex;
  flex-direction: column;
  padding: 0;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px;
  border-bottom: 1px solid #1e293b;
}
.logo-icon { font-size: 24px; }
.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.nav-menu {
  border-right: none;
  background: transparent;
  flex: 1;
  --el-menu-text-color: #94a3b8;
  --el-menu-active-color: #a855f7;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: #1e293b;
}
.main-content {
  background: #0f172a;
  padding: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
/* 让直接子元素铺满 */
.main-content > * {
  flex: 1;
  min-height: 0;
}
</style>
