/**
 * 通知 API
 */
import request from './index'

export interface NotificationItem {
    id: string
    type: string
    title: string
    content: string | null
    is_read: boolean
    related_id: string | null
    created_at: string
}

export interface NotificationList {
    notifications: NotificationItem[]
    total: number
    unread_count: number
}

/** 获取通知列表 */
export function getNotifications(params?: {
    skip?: number
    limit?: number
    unread_only?: boolean
}): Promise<NotificationList> {
    return request({ url: '/api/v1/user/notifications', method: 'get', params })
}

/** 获取未读数 */
export function getUnreadCount(): Promise<{ unread_count: number }> {
    return request({ url: '/api/v1/user/notifications/unread-count', method: 'get' })
}

/** 标记单条已读 */
export function markAsRead(id: string): Promise<{ detail: string }> {
    return request({ url: `/api/v1/user/notifications/${id}/read`, method: 'put' })
}

/** 全部已读 */
export function markAllRead(): Promise<{ detail: string }> {
    return request({ url: '/api/v1/user/notifications/read-all', method: 'put' })
}
