/**
 * 用户相关类型定义
 */

export interface User {
  id: string
  email: string
  full_name: string | null
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}
