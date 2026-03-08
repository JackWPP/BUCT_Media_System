<template>
  <div class="settings-container">
    <n-space vertical size="large">
      <n-card title="运行时摘要">
        <n-spin :show="loading">
          <n-grid :cols="3" :x-gap="16" :y-gap="16" responsive="screen">
            <n-grid-item>
              <n-statistic label="AI 分析">
                <n-tag :type="settings.ai_enabled ? 'success' : 'default'">
                  {{ settings.ai_enabled ? '已启用' : '已关闭' }}
                </n-tag>
              </n-statistic>
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="当前默认 Provider">
                <n-text>{{ settings.default_provider?.display_name || '环境变量回退 / 未配置' }}</n-text>
              </n-statistic>
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="当前模型">
                <n-text>{{ settings.default_provider?.model_id || '-' }}</n-text>
              </n-statistic>
            </n-grid-item>
          </n-grid>
        </n-spin>
      </n-card>

      <n-card title="内容与访问策略">
        <n-spin :show="loading">
          <n-form label-placement="left" label-width="180" style="max-width: 760px;">
            <n-form-item label="人像照片可见性">
              <n-radio-group v-model:value="settings.portrait_visibility">
                <n-space vertical>
                  <n-radio value="public">公开访问</n-radio>
                  <n-radio value="login_required">登录后可见</n-radio>
                  <n-radio value="authorized_only">仅授权用户</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="AI 分析开关">
              <n-switch v-model:value="settings.ai_enabled" />
            </n-form-item>
            <n-space>
              <n-button type="primary" :loading="savingSettings" @click="handleSaveSettings">保存设置</n-button>
              <n-button @click="fetchAll">重载</n-button>
            </n-space>
          </n-form>
        </n-spin>
      </n-card>

      <n-card>
        <template #header>
          <n-space justify="space-between" align="center">
            <span>AI 供应商管理</span>
            <n-space>
              <n-button @click="fetchProviders" :loading="loadingProviders">刷新</n-button>
              <n-button type="primary" @click="openCreateModal">新增 Provider</n-button>
            </n-space>
          </n-space>
        </template>

        <n-empty v-if="!loadingProviders && providers.length === 0" description="暂无 AI Provider 配置" />

        <n-grid v-else :cols="2" :x-gap="16" :y-gap="16" responsive="screen">
          <n-grid-item v-for="provider in providers" :key="provider.id">
            <n-card size="small" embedded>
              <n-space vertical>
                <n-space justify="space-between" align="center">
                  <n-space align="center">
                    <n-tag :type="provider.is_default ? 'success' : 'default'">
                      {{ provider.is_default ? '默认' : provider.provider_type }}
                    </n-tag>
                    <n-text strong>{{ provider.display_name }}</n-text>
                  </n-space>
                  <n-switch
                    :value="provider.enabled"
                    :loading="providerActionId === provider.id"
                    @update:value="(value: boolean) => handleToggleProvider(provider, value)"
                  />
                </n-space>

                <n-descriptions :column="1" size="small" bordered>
                  <n-descriptions-item label="Provider 类型">{{ provider.provider_type }}</n-descriptions-item>
                  <n-descriptions-item label="Base URL">{{ provider.base_url }}</n-descriptions-item>
                  <n-descriptions-item label="模型 ID">{{ provider.model_id }}</n-descriptions-item>
                  <n-descriptions-item label="API Key">
                    {{ provider.secret.has_api_key ? provider.secret.masked_value : '未配置' }}
                  </n-descriptions-item>
                  <n-descriptions-item label="超时 / 重试 / 预算">
                    {{ provider.timeout_seconds }}s / {{ provider.max_retries }} / {{ provider.daily_budget }}
                  </n-descriptions-item>
                  <n-descriptions-item label="最近探活">
                    <n-tag
                      size="small"
                      :type="provider.last_test_status === 'success' ? 'success' : provider.last_test_status === 'failed' ? 'error' : 'default'"
                    >
                      {{ provider.last_test_status || '未测试' }}
                    </n-tag>
                    <n-text depth="3" style="margin-left: 8px;">{{ provider.last_test_message || '-' }}</n-text>
                  </n-descriptions-item>
                </n-descriptions>

                <n-space>
                  <n-button size="small" @click="openEditModal(provider)" :loading="providerActionId === provider.id">编辑</n-button>
                  <n-button
                    size="small"
                    type="primary"
                    secondary
                    :disabled="provider.is_default"
                    :loading="providerActionId === provider.id"
                    @click="handleSetDefault(provider)"
                  >
                    设为默认
                  </n-button>
                  <n-button
                    size="small"
                    tertiary
                    :loading="providerActionId === provider.id"
                    @click="handleTestProvider(provider)"
                  >
                    测试连接
                  </n-button>
                </n-space>
              </n-space>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-card>

      <n-card title="基础设施概览">
        <n-descriptions :column="1" bordered>
          <n-descriptions-item label="数据库">{{ settings.database_backend }}</n-descriptions-item>
          <n-descriptions-item label="存储后端">{{ settings.storage_backend }}</n-descriptions-item>
          <n-descriptions-item label="任务队列">{{ settings.task_queue_backend }}</n-descriptions-item>
        </n-descriptions>
        <n-alert type="info" style="margin-top: 16px;">
          数据库、对象存储和任务队列这类基础设施配置仍由部署环境控制，这里只做状态展示，不支持在线修改。
        </n-alert>
      </n-card>
    </n-space>

    <n-modal
      v-model:show="showProviderModal"
      preset="dialog"
      :title="editingProviderId ? '编辑 AI Provider' : '新增 AI Provider'"
      positive-text="保存"
      negative-text="取消"
      @positive-click="handleSaveProvider"
    >
      <n-form ref="providerFormRef" :model="providerForm" label-placement="left" label-width="120">
        <n-form-item label="Provider 类型">
          <n-select v-model:value="providerForm.provider_type" :options="providerTypeOptions" :disabled="!!editingProviderId" />
        </n-form-item>
        <n-form-item label="显示名称">
          <n-input v-model:value="providerForm.display_name" placeholder="例如 阿里云百炼生产" />
        </n-form-item>
        <n-form-item label="Base URL">
          <n-input v-model:value="providerForm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </n-form-item>
        <n-form-item label="模型 ID">
          <n-input v-model:value="providerForm.model_id" placeholder="例如 qwen-vl-max" />
        </n-form-item>
        <n-form-item v-if="providerNeedsApiKey" label="API Key">
          <n-input
            v-model:value="providerForm.api_key"
            type="password"
            show-password-on="click"
            :placeholder="editingProviderId && providerForm.has_api_key ? '留空则保留原 Key' : '输入 API Key'"
          />
        </n-form-item>
        <n-form-item v-if="editingProviderId && providerForm.has_api_key" label="密钥操作">
          <n-checkbox v-model:checked="providerForm.clear_api_key">清空当前 API Key</n-checkbox>
        </n-form-item>
        <n-form-item label="超时秒数">
          <n-input-number v-model:value="providerForm.timeout_seconds" :min="5" :max="300" style="width: 100%;" />
        </n-form-item>
        <n-form-item label="最大重试">
          <n-input-number v-model:value="providerForm.max_retries" :min="0" :max="5" style="width: 100%;" />
        </n-form-item>
        <n-form-item label="每日预算">
          <n-input-number v-model:value="providerForm.daily_budget" :min="0" :max="100000" style="width: 100%;" />
        </n-form-item>
        <n-form-item v-if="providerSupportsExtraHeaders" label="额外 Headers">
          <n-input
            v-model:value="providerForm.extra_headers_text"
            type="textarea"
            :rows="4"
            placeholder='JSON，例如 {"X-Provider": "demo"}'
          />
        </n-form-item>
        <n-form-item label="启用">
          <n-switch v-model:value="providerForm.enabled" />
        </n-form-item>
        <n-form-item label="默认 Provider">
          <n-switch v-model:value="providerForm.is_default" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import * as settingsApi from '../../api/settings'
import type {
  AIProviderConfigDetail,
  AIProviderConfigSummary,
  AIProviderPayload,
  AIProviderType,
  PortraitVisibility,
  SystemSettings,
} from '../../api/settings'

const message = useMessage()

const loading = ref(false)
const loadingProviders = ref(false)
const savingSettings = ref(false)
const providerActionId = ref<string | null>(null)
const showProviderModal = ref(false)
const editingProviderId = ref<string | null>(null)

const settings = reactive<SystemSettings>({
  portrait_visibility: 'login_required',
  ai_enabled: true,
  storage_backend: 'local',
  task_queue_backend: 'background',
  database_backend: 'sqlite',
  default_provider: null,
})

const providers = ref<AIProviderConfigSummary[]>([])

const providerForm = reactive({
  provider_type: 'dashscope' as AIProviderType,
  display_name: '',
  enabled: true,
  is_default: false,
  base_url: '',
  model_id: '',
  api_key: '',
  has_api_key: false,
  clear_api_key: false,
  timeout_seconds: 60,
  max_retries: 2,
  daily_budget: 500,
  extra_headers_text: '{}',
})

const providerTypeOptions = [
  { label: 'DashScope / 百炼', value: 'dashscope' },
  { label: 'Ollama', value: 'ollama' },
  { label: 'OpenAI Compatible', value: 'openai_compatible' },
]

const providerNeedsApiKey = computed(() => providerForm.provider_type !== 'ollama')
const providerSupportsExtraHeaders = computed(() => providerForm.provider_type === 'openai_compatible')

onMounted(() => {
  fetchAll()
})

async function fetchAll() {
  loading.value = true
  try {
    await Promise.all([fetchSettings(), fetchProviders()])
  } finally {
    loading.value = false
  }
}

async function fetchSettings() {
  const data = await settingsApi.getSettings()
  Object.assign(settings, data)
}

async function fetchProviders() {
  loadingProviders.value = true
  try {
    providers.value = await settingsApi.getAIProviders()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载 AI Provider 失败')
  } finally {
    loadingProviders.value = false
  }
}

async function handleSaveSettings() {
  savingSettings.value = true
  try {
    await settingsApi.updatePortraitVisibility(settings.portrait_visibility as PortraitVisibility)
    await settingsApi.updateAISettings(settings.ai_enabled)
    await fetchSettings()
    message.success('系统设置已保存')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存系统设置失败')
  } finally {
    savingSettings.value = false
  }
}

function resetProviderForm() {
  providerForm.provider_type = 'dashscope'
  providerForm.display_name = ''
  providerForm.enabled = true
  providerForm.is_default = false
  providerForm.base_url = ''
  providerForm.model_id = ''
  providerForm.api_key = ''
  providerForm.has_api_key = false
  providerForm.clear_api_key = false
  providerForm.timeout_seconds = 60
  providerForm.max_retries = 2
  providerForm.daily_budget = 500
  providerForm.extra_headers_text = '{}'
}

function openCreateModal() {
  editingProviderId.value = null
  resetProviderForm()
  showProviderModal.value = true
}

async function openEditModal(provider: AIProviderConfigSummary) {
  providerActionId.value = provider.id
  try {
    const detail = await settingsApi.getAIProvider(provider.id)
    editingProviderId.value = provider.id
    fillProviderForm(detail)
    showProviderModal.value = true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载 Provider 详情失败')
  } finally {
    providerActionId.value = null
  }
}

function fillProviderForm(provider: AIProviderConfigDetail) {
  providerForm.provider_type = provider.provider_type
  providerForm.display_name = provider.display_name
  providerForm.enabled = provider.enabled
  providerForm.is_default = provider.is_default
  providerForm.base_url = provider.base_url
  providerForm.model_id = provider.model_id
  providerForm.api_key = ''
  providerForm.has_api_key = provider.secret.has_api_key
  providerForm.clear_api_key = false
  providerForm.timeout_seconds = provider.timeout_seconds
  providerForm.max_retries = provider.max_retries
  providerForm.daily_budget = provider.daily_budget
  providerForm.extra_headers_text = JSON.stringify(provider.extra_headers_json || {}, null, 2)
}

function buildProviderPayload(): AIProviderPayload {
  let extraHeaders: Record<string, string> = {}
  if (providerSupportsExtraHeaders.value && providerForm.extra_headers_text.trim()) {
    extraHeaders = JSON.parse(providerForm.extra_headers_text)
  }
  return {
    provider_type: providerForm.provider_type,
    display_name: providerForm.display_name.trim(),
    enabled: providerForm.enabled,
    is_default: providerForm.is_default,
    base_url: providerForm.base_url.trim(),
    model_id: providerForm.model_id.trim(),
    api_key: providerForm.api_key.trim() || null,
    clear_api_key: providerForm.clear_api_key,
    extra_headers_json: extraHeaders,
    timeout_seconds: providerForm.timeout_seconds,
    max_retries: providerForm.max_retries,
    daily_budget: providerForm.daily_budget,
  }
}

async function handleSaveProvider() {
  try {
    const payload = buildProviderPayload()
    if (editingProviderId.value) {
      await settingsApi.updateAIProvider(editingProviderId.value, payload)
      message.success('AI Provider 已更新')
    } else {
      await settingsApi.createAIProvider(payload)
      message.success('AI Provider 已创建')
    }
    await Promise.all([fetchProviders(), fetchSettings()])
    return true
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    message.error(typeof detail === 'string' ? detail : '保存 AI Provider 失败')
    return false
  }
}

async function handleSetDefault(provider: AIProviderConfigSummary) {
  providerActionId.value = provider.id
  try {
    await settingsApi.setDefaultAIProvider(provider.id)
    await Promise.all([fetchProviders(), fetchSettings()])
    message.success('默认 Provider 已切换')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '切换默认 Provider 失败')
  } finally {
    providerActionId.value = null
  }
}

async function handleToggleProvider(provider: AIProviderConfigSummary, enabled: boolean) {
  providerActionId.value = provider.id
  try {
    await settingsApi.toggleAIProvider(provider.id, enabled)
    await Promise.all([fetchProviders(), fetchSettings()])
    message.success(enabled ? 'Provider 已启用' : 'Provider 已停用')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '更新 Provider 状态失败')
  } finally {
    providerActionId.value = null
  }
}

async function handleTestProvider(provider: AIProviderConfigSummary) {
  providerActionId.value = provider.id
  try {
    const result = await settingsApi.testAIProvider(provider.id)
    await Promise.all([fetchProviders(), fetchSettings()])
    if (result.success) {
      message.success('连接测试成功')
    } else {
      message.warning(result.message)
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '连接测试失败')
  } finally {
    providerActionId.value = null
  }
}
</script>

<style scoped>
.settings-container {
  max-width: 1280px;
  margin: 0 auto;
}
</style>
