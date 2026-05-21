import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/chat/ChatView.vue'),
    meta: { title: 'AI 对话' },
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('@/views/upload/UploadView.vue'),
    meta: { title: '上传文档' },
  },
  {
    path: '/files',
    name: 'Files',
    component: () => import('@/views/files/FilesView.vue'),
    meta: { title: '文件管理' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/SettingsView.vue'),
    meta: { title: '系统设置' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title ?? 'NovaMind'} - NovaMind`
})

export default router
