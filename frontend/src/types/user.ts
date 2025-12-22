/**
 * 用户相关类型定义
 */

/**
 * 用户角色类型
 * - admin: 超级管理员，拥有所有权限
 * - auditor: 审核员，可审核照片和编辑标签
 * - dept_user: 部门用户，预留扩展
 * - user: 普通用户
 */
export type UserRole = 'admin' | 'auditor' | 'dept_user' | 'user'

export interface User {
  id: string
  email: string
  full_name: string | null
  student_id: string | null  // 学号/工号，核心身份标识
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  identifier: string  // 学号或邮箱
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

/**
 * 管理员创建用户请求
 */
export interface UserCreateRequest {
  email: string
  full_name?: string
  password: string
  role?: UserRole
  student_id?: string  // 学号/工号
}

/**
 * 管理员更新用户请求
 */
export interface UserUpdateRequest {
  email?: string
  full_name?: string
  password?: string
  is_active?: boolean
  role?: UserRole
  student_id?: string
}

/**
 * 用户列表响应
 */
export interface UserListResponse {
  users: User[]
  total: number
}

