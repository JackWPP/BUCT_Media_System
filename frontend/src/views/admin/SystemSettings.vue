<template>
  <div class="settings-container">
    <n-space vertical size="large">
      <n-card title="系统设置">
        <n-spin :show="loading">
          <n-form :model="settings" label-placement="left" label-width="180" style="max-width: 760px;">
            <n-form-item label="人像照片可见性">
              <n-radio-group v-model:value="settings.portrait_visibility">
                <n-space vertical>
                  <n-radio value="public">公开访问</n-radio>
                  <n-radio value="login_required">登录后可见</n-radio>
                  <n-radio value="authorized_only">仅授权用户</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-divider />

            <n-form-item label="AI 分析开关">
              <n-switch v-model:value="settings.ai_enabled" />
            </n-form-item>

            <n-form-item label="AI Provider">
              <n-radio-group v-model:value="settings.ai_provider">
                <n-space>
                  <n-radio value="ollama">Ollama</n-radio>
                  <n-radio value="dashscope">DashScope / 百炼</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item label="AI 模型 ID">
              <n-input v-model:value="settings.ai_model_id" placeholder="例如 llava 或 qwen-vl-max" />
            </n-form-item>

            <n-divider />

            <n-form-item label="存储后端">
              <n-tag type="info">{{ settings.storage_backend }}</n-tag>
            </n-form-item>

            <n-form-item label="任务队列后端">
              <n-tag type="info">{{ settings.task_queue_backend }}</n-tag>
            </n-form-item>

            <n-alert type="info" title="说明" style="margin-bottom: 16px;">
              存储后端和任务队列后端由服务器环境变量控制，这里只做展示。人像访问策略和 AI 行为可以在当前页面直接调整。
            </n-alert>

            <n-space>
              <n-button type="primary" :loading="saving" @click="handleSave">保存设置</n-button>
              <n-button @click="fetchSettings">重置</n-button>
            </n-space>
          </n-form>
        </n-spin>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import * as settingsApi from '../../api/settings'
import type { AIProvider, PortraitVisibility, SystemSettings } from '../../api/settings'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)

const settings = reactive<SystemSettings>({
  portrait_visibility: 'login_required',
  ai_enabled: true,
  ai_provider: 'ollama',
  ai_model_id: '',
  storage_backend: 'local',
  task_queue_backend: 'background',
})

onMounted(() => {
  fetchSettings()
})

async function fetchSettings() {
  loading.value = true
  try {
    const data = await settingsApi.getSettings()
    settings.portrait_visibility = data.portrait_visibility
    settings.ai_enabled = data.ai_enabled
    settings.ai_provider = data.ai_provider
    settings.ai_model_id = data.ai_model_id
    settings.storage_backend = data.storage_backend
    settings.task_queue_backend = data.task_queue_backend
  } catch {
    message.error('加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await settingsApi.updatePortraitVisibility(settings.portrait_visibility as PortraitVisibility)
    await settingsApi.updateAISettings({
      enabled: settings.ai_enabled,
      provider: settings.ai_provider as AIProvider,
      model_id: settings.ai_model_id,
    })
    message.success('设置已保存')
    await fetchSettings()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存系统设置失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-container {
  max-width: 960px;
  margin: 0 auto;
}
</style>
