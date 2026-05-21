<template>
  <app-layout>
    <div class="upload-page">
      <div class="page-header">
        <h1>上传文档</h1>
        <p>支持 PDF 格式，系统将自动解析并向量化存入知识库</p>
      </div>

      <el-upload
        class="upload-dragger"
        drag
        action=""
        :auto-upload="false"
        :on-change="handleFileChange"
        accept=".pdf"
        :show-file-list="false"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">拖拽 PDF 文件到此处，或 <em>点击上传</em></div>
        <div class="upload-hint">仅支持 .pdf 格式，文件将自动去重</div>
      </el-upload>

      <!-- 文件队列 -->
      <div v-if="queue.length" class="queue-list">
        <div v-for="item in queue" :key="item.name" class="queue-item">
          <div class="queue-name">📄 {{ item.name }}</div>
          <div class="queue-size">{{ formatSize(item.size) }}</div>
          <el-tag :type="statusType(item.status)" size="small">{{ item.status }}</el-tag>
        </div>
      </div>

      <el-button
        v-if="pendingFiles.length"
        type="primary"
        :loading="uploading"
        @click="uploadAll"
        class="upload-btn"
      >
        开始上传 ({{ pendingFiles.length }} 个文件)
      </el-button>
    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { fileApi } from '@/api/file'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

interface QueueItem {
  name: string
  size: number
  file: File
  status: 'pending' | 'uploading' | 'done' | 'failed' | 'duplicate'
}

const queue = ref<QueueItem[]>([])
const uploading = ref(false)

const pendingFiles = computed(() => queue.value.filter((f) => f.status === 'pending'))

function handleFileChange(uploadFile: UploadFile) {
  if (!uploadFile.raw) return
  queue.value.push({ name: uploadFile.name, size: uploadFile.raw.size, file: uploadFile.raw, status: 'pending' })
}

function formatSize(bytes: number): string {
  return bytes > 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${(bytes / 1024).toFixed(0)} KB`
}

function statusType(status: string) {
  return { done: 'success', failed: 'danger', duplicate: 'warning', uploading: '', pending: 'info' }[status] as any
}

async function uploadAll() {
  uploading.value = true
  for (const item of pendingFiles.value) {
    item.status = 'uploading'
    try {
      await fileApi.upload(item.file)
      item.status = 'done'
    } catch (e: any) {
      item.status = e?.response?.status === 409 ? 'duplicate' : 'failed'
    }
  }
  uploading.value = false
  ElMessage.success('上传完成')
}
</script>

<style scoped>
.upload-page {
  padding: 40px;
  color: #cbd5e1;
  max-width: 800px;
  margin: 0 auto;
}
.page-header { margin-bottom: 32px; }
.page-header h1 { font-size: 28px; font-weight: 700; color: #f1f5f9; margin-bottom: 8px; }
.page-header p { color: #64748b; }
.upload-dragger { width: 100%; }
:deep(.el-upload-dragger) {
  background: #1e293b;
  border-color: #334155;
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.upload-icon { font-size: 48px; color: #6366f1; margin-bottom: 12px; }
.upload-text { color: #94a3b8; font-size: 16px; }
.upload-text em { color: #a855f7; font-style: normal; }
.upload-hint { font-size: 12px; color: #475569; margin-top: 6px; }
.queue-list { margin-top: 24px; display: flex; flex-direction: column; gap: 10px; }
.queue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #1e293b;
  border-radius: 8px;
}
.queue-name { flex: 1; font-size: 14px; }
.queue-size { color: #475569; font-size: 12px; min-width: 70px; text-align: right; }
.upload-btn { margin-top: 24px; }
</style>
