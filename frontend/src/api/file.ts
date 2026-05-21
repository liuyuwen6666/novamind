import http from '@/utils/http'
import type { ApiResponse, FileItem, FileUploadResponse } from '@/types'

export const fileApi = {
  upload(file: File, workspaceId?: string): Promise<{ data: ApiResponse<FileUploadResponse> }> {
    const form = new FormData()
    form.append('file', file)
    if (workspaceId) form.append('workspace_id', workspaceId)
    return http.post('/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list(workspaceId?: string): Promise<{ data: ApiResponse<FileItem[]> }> {
    return http.get('/files/', { params: { workspace_id: workspaceId } })
  },

  delete(fileId: string): Promise<{ data: ApiResponse<null> }> {
    return http.delete(`/files/${fileId}`)
  },
}
