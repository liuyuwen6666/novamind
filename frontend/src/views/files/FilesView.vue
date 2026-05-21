<template>
  <app-layout>
    <div class="files-page">
      <div class="page-header">
        <h1>文件管理</h1>
        <el-button @click="fileStore.fetchFiles()" :loading="fileStore.loading" icon="Refresh">
          刷新
        </el-button>
      </div>

      <el-table
        :data="fileStore.files"
        v-loading="fileStore.loading"
        empty-text="暂无文件"
        class="files-table"
      >
        <el-table-column prop="file_name" label="文件名" />
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-popconfirm title="确认删除该文件？" @confirm="fileStore.deleteFile(row.id)">
              <template #reference>
                <el-button type="danger" size="small" icon="Delete" />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { useFileStore } from '@/stores/file'

const fileStore = useFileStore()
onMounted(() => fileStore.fetchFiles())

function formatSize(bytes: number) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`
}
function statusType(s: string) {
  return { done: 'success', failed: 'danger', processing: 'warning', pending: 'info' }[s] as any
}
function formatDate(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.files-page { padding: 40px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.page-header h1 { font-size: 28px; font-weight: 700; color: #f1f5f9; }
.files-table {
  background: transparent;
  --el-table-bg-color: #1e293b;
  --el-table-tr-bg-color: #1e293b;
  --el-table-header-bg-color: #0f172a;
  --el-table-text-color: #cbd5e1;
  --el-table-header-text-color: #94a3b8;
  --el-table-border-color: #334155;
}
</style>
