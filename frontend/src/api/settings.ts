/**
 * 系统设置 API
 * 
 * 仅限管理员使用。
 */
import request from './index'

const BASE_URL = '/api/v1/admin/settings'

/**
 * 人像照片可见性选项
 */
export type PortraitVisibility = 'public' | 'login_required' | 'authorized_only'

export interface SystemSettings {
    portrait_visibility: PortraitVisibility
}

/**
 * 获取系统设置
 */
export async function getSettings(): Promise<SystemSettings> {
    return request({
        url: BASE_URL,
        method: 'get'
    })
}

/**
 * 更新人像照片可见性
 */
export async function updatePortraitVisibility(visibility: PortraitVisibility): Promise<SystemSettings> {
    return request({
        url: `${BASE_URL}/portrait-visibility`,
        method: 'put',
        data: { visibility }
    })
}

/**
 * 获取人像照片可见性（公开接口）
 */
export async function getPortraitVisibility(): Promise<{ portrait_visibility: PortraitVisibility }> {
    return request({
        url: `${BASE_URL}/portrait-visibility`,
        method: 'get'
    })
}
