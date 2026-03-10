/**
 * 审计日志 API
 */
import request from './index'

export interface AuditLogItem {
    id: string
    user_id: string | null
    user_name: string | null
    user_student_id: string | null
    action: string
    resource_type: string | null
    resource_id: string | null
    detail: string | null
    ip_address: string | null
    created_at: string
}

export interface AuditLogList {
    logs: AuditLogItem[]
    total: number
}

export interface AuditLogQuery {
    skip?: number
    limit?: number
    action?: string
    user_id?: string
    resource_type?: string
}

/**
 * 获取审计日志列表
 */
export function getAuditLogs(params?: AuditLogQuery): Promise<AuditLogList> {
    return request({
        url: '/api/v1/admin/audit-logs',
        method: 'get',
        params,
    })
}
