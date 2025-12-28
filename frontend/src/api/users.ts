/**
 * 用户管理 API
 * 
 * 仅限管理员使用。
 */
import request from './index'
import type {
    User,
    UserListResponse,
    UserCreateRequest,
    UserUpdateRequest,
    UserRole
} from '../types/user'

const BASE_URL = '/api/v1/admin/users'

/**
 * 获取用户列表
 */
export async function getUsers(params?: {
    skip?: number
    limit?: number
    search?: string
    role?: UserRole
}): Promise<UserListResponse> {
    return request({
        url: BASE_URL,
        method: 'get',
        params
    })
}

/**
 * 获取单个用户
 */
export async function getUser(userId: string): Promise<User> {
    return request.get(`${BASE_URL}/${userId}`)
}

/**
 * 创建用户
 */
export async function createUser(data: UserCreateRequest): Promise<User> {
    return request.post(BASE_URL, data)
}

/**
 * 更新用户
 */
export async function updateUser(userId: string, data: UserUpdateRequest): Promise<User> {
    return request.put(`${BASE_URL}/${userId}`, data)
}

/**
 * 修改用户角色
 */
export async function updateUserRole(userId: string, role: UserRole): Promise<User> {
    return request.put(`${BASE_URL}/${userId}/role`, { role })
}

/**
 * 删除用户
 */
export async function deleteUser(userId: string): Promise<void> {
    return request.delete(`${BASE_URL}/${userId}`)
}
