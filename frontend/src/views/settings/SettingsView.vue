<template>
  <app-layout>
    <div class="settings-page">
      <div class="page-header">
        <h1>系统设置</h1>
      </div>
      <el-descriptions title="当前配置" :column="1" border class="settings-card">
        <el-descriptions-item label="LLM 模型">{{ config.llmModel }}</el-descriptions-item>
        <el-descriptions-item label="Embedding 模型">{{ config.embeddingModel }}</el-descriptions-item>
        <el-descriptions-item label="Chunk Size">{{ config.chunkSize }}</el-descriptions-item>
        <el-descriptions-item label="Chunk Overlap">{{ config.chunkOverlap }}</el-descriptions-item>
        <el-descriptions-item label="RAG Top-K">{{ config.ragTopK }}</el-descriptions-item>
      </el-descriptions>
      <el-alert type="info" :closable="false" class="settings-note">
        配置项通过后端 .env 文件管理，请修改 backend/.env 后重启服务。
      </el-alert>
    </div>
  </app-layout>
</template>

<script setup lang="ts">
import AppLayout from '@/components/common/AppLayout.vue'

const config = {
  llmModel: 'LongCat',
  embeddingModel: '字节/火山 Embedding (doubao-embedding)',
  chunkSize: 500,
  chunkOverlap: 100,
  ragTopK: 5,
}
</script>

<style scoped>
.settings-page { padding: 40px; max-width: 700px; }
.page-header { margin-bottom: 32px; }
.page-header h1 { font-size: 28px; font-weight: 700; color: #f1f5f9; }
.settings-card {
  --el-descriptions-item-bordered-label-background: #1e293b;
  --el-fill-color-blank: #0f172a;
  --el-border-color: #334155;
  --el-text-color-primary: #cbd5e1;
}
.settings-note { margin-top: 24px; background: #1e293b; border-color: #334155; }
</style>
