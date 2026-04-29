/**
 * Admin system settings API.
 */
import request from './index'

const SETTINGS_BASE_URL = '/api/v1/admin/settings'
const PROVIDERS_BASE_URL = '/api/v1/admin/ai-providers'

export type PortraitVisibility = 'public' | 'login_required' | 'authorized_only'
export type AIProviderType = 'ollama' | 'dashscope' | 'openai_compatible'

export interface RuntimeProviderSummary {
  provider_type: AIProviderType
  display_name: string
  model_id: string
  base_url: string
  source: string
  timeout_seconds: number
  max_retries: number
  daily_budget: number
}

export interface SystemSettings {
  portrait_visibility: PortraitVisibility
  ai_enabled: boolean
  ai_search_enabled: boolean
  ai_search_provider: string | null
  ai_search_model_id: string | null
  storage_backend: string
  task_queue_backend: string
  database_backend: string
  default_provider: RuntimeProviderSummary | null
}

export interface AIProviderMaskedSecret {
  has_api_key: boolean
  masked_value: string | null
}

export interface AIProviderConfigSummary {
  id: string
  provider_type: AIProviderType
  display_name: string
  enabled: boolean
  is_default: boolean
  base_url: string
  model_id: string
  timeout_seconds: number
  max_retries: number
  daily_budget: number
  last_test_status: string | null
  last_test_message: string | null
  last_tested_at: string | null
  updated_at: string
  secret: AIProviderMaskedSecret
}

export interface AIProviderConfigDetail extends AIProviderConfigSummary {
  extra_headers_json: Record<string, string>
}

export interface AIProviderPayload {
  provider_type: AIProviderType
  display_name: string
  enabled: boolean
  is_default?: boolean
  base_url: string
  model_id: string
  api_key?: string | null
  clear_api_key?: boolean
  extra_headers_json: Record<string, string>
  timeout_seconds: number
  max_retries: number
  daily_budget: number
}

export interface AIProviderTestResult {
  success: boolean
  message: string
  checked_at: string
}

export async function getSettings(): Promise<SystemSettings> {
  return request({
    url: SETTINGS_BASE_URL,
    method: 'get',
  })
}

export async function updatePortraitVisibility(visibility: PortraitVisibility): Promise<SystemSettings> {
  return request({
    url: `${SETTINGS_BASE_URL}/portrait-visibility`,
    method: 'put',
    data: { visibility },
  })
}

export async function updateAISettings(enabled: boolean): Promise<SystemSettings> {
  return request({
    url: `${SETTINGS_BASE_URL}/ai`,
    method: 'put',
    data: { enabled },
  })
}

export async function updateAISearchSettings(
  enabled: boolean,
  provider?: string,
  modelId?: string,
): Promise<SystemSettings> {
  return request({
    url: `${SETTINGS_BASE_URL}/ai-search`,
    method: 'put',
    data: { enabled, provider, model_id: modelId },
  })
}

export async function getPortraitVisibility(): Promise<{ portrait_visibility: PortraitVisibility }> {
  return request({
    url: `${SETTINGS_BASE_URL}/portrait-visibility`,
    method: 'get',
  })
}

export async function getAIProviders(): Promise<AIProviderConfigSummary[]> {
  return request({
    url: PROVIDERS_BASE_URL,
    method: 'get',
  })
}

export async function getAIProvider(providerId: string): Promise<AIProviderConfigDetail> {
  return request({
    url: `${PROVIDERS_BASE_URL}/${providerId}`,
    method: 'get',
  })
}

export async function createAIProvider(data: AIProviderPayload): Promise<AIProviderConfigDetail> {
  return request({
    url: PROVIDERS_BASE_URL,
    method: 'post',
    data,
  })
}

export async function updateAIProvider(providerId: string, data: Partial<AIProviderPayload>): Promise<AIProviderConfigDetail> {
  return request({
    url: `${PROVIDERS_BASE_URL}/${providerId}`,
    method: 'put',
    data,
  })
}

export async function testAIProvider(providerId: string): Promise<AIProviderTestResult> {
  return request({
    url: `${PROVIDERS_BASE_URL}/${providerId}/test`,
    method: 'post',
  })
}

export async function setDefaultAIProvider(providerId: string): Promise<AIProviderConfigDetail> {
  return request({
    url: `${PROVIDERS_BASE_URL}/${providerId}/set-default`,
    method: 'post',
  })
}

export async function toggleAIProvider(providerId: string, enabled: boolean): Promise<AIProviderConfigDetail> {
  return request({
    url: `${PROVIDERS_BASE_URL}/${providerId}/toggle`,
    method: 'post',
    data: { enabled },
  })
}
