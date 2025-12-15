/**
 * 统计相关 API
 */
import request from './index'

export interface DashboardStats {
    total_photos: number
    total_views: number
    total_storage: number
    daily_uploads: { date: string; count: number }[]
    popular_tags: { name: string; count: number }[]
    top_photos: { id: string; filename: string; views: number; thumb_path?: string }[]
}

/**
 * 获取仪表盘统计数据
 */
export function getDashboardStats(): Promise<DashboardStats> {
    return request({
        url: '/api/v1/stats/dashboard',
        method: 'get',
    })
}

/**
 * 增加照片浏览量
 */
export function incrementView(photoId: string): Promise<{ message: string; views: number }> {
    return request({
        url: `/api/v1/stats/view/${photoId}`,
        method: 'post',
    })
}
