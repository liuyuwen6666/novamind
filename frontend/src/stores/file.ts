import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { FileItem } from '@/types'
import { fileApi } from '@/api/file'
import { ElMessage } from 'element-plus'

export const useFileStore = defineStore('file', () => {
  const files = ref<FileItem[]>([])
  const loading = ref(false)

  async function fetchFiles(workspaceId?: string) {
    loading.value = true
    try {
      const res = await fileApi.list(workspaceId)
      files.value = res.data.data ?? []
    } catch {
      // 错误已在 http.ts 中统一处理
    } finally {
      loading.value = false
    }
  }

  async function deleteFile(fileId: string) {
    await fileApi.delete(fileId)
    files.value = files.value.filter((f) => f.id !== fileId)
    ElMessage.success('文件已删除')
  }

  return { files, loading, fetchFiles, deleteFile }
})
