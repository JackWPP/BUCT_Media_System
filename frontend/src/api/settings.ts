/**
 * Admin system settings API.
 */
import request from './index'

const BASE_URL = '/api/v1/admin/settings'

export type PortraitVisibility = 'public' | 'login_required' | 'authorized_only'
export type AIProvider = 'ollama' | 'dashscope'

export interface SystemSettings {
  portrait_visibility: PortraitVisibility
  ai_enabled: boolean
  ai_provider: AIProvider
  ai_model_id: string
  storage_backend: string
  task_queue_backend: string
}

export async function getSettings(): Promise<SystemSettings> {
  return request({
    url: BASE_URL,
    method: 'get',
  })
}

export async function updatePortraitVisibility(visibility: PortraitVisibility): Promise<SystemSettings> {
  return request({
    url: `${BASE_URL}/portrait-visibility`,
    method: 'put',
    data: { visibility },
  })
}

export async function updateAISettings(data: {
  enabled: boolean
  provider: AIProvider
  model_id: string
}): Promise<SystemSettings> {
  return request({
    url: `${BASE_URL}/ai`,
    method: 'put',
    data,
  })
}

export async function getPortraitVisibility(): Promise<{ portrait_visibility: PortraitVisibility }> {
  return request({
    url: `${BASE_URL}/portrait-visibility`,
    method: 'get',
  })
}
