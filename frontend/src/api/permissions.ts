/**
 * 权限管理 API
 */
import request from './index'

export interface PermissionResponse {
    id: string
    user_id: string
    user_student_id: string
    user_name: string
    resource_type: string
    resource_key: string
    permission_type: string
    start_time: string
    end_time: string | null
    is_active: boolean
    created_at: string
    note: string | null
}

export interface PermissionListResponse {
    permissions: PermissionResponse[]
    total: number
}

export interface PermissionGrantRequest {
    student_id: string
    resource_type: string
    resource_key: string
    permission_type: string
    days: number | null
    note?: string
}

/**
 * 获取用户的权限列表
 */
export function getUserPermissions(studentId: string): Promise<PermissionListResponse> {
    return request({
        url: `/api/v1/admin/permissions/user/${studentId}`,
        method: 'get',
    })
}

/**
 * 授予权限
 */
export function grantPermission(data: PermissionGrantRequest): Promise<PermissionResponse> {
    return request({
        url: '/api/v1/admin/permissions/grant',
        method: 'post',
        data,
    })
}

/**
 * 撤销权限
 */
export function revokePermission(permissionId: string): Promise<void> {
    return request({
        url: `/api/v1/admin/permissions/${permissionId}`,
        method: 'delete',
    })
}
