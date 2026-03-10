/**
 * 认证相关 API
 */
import request from './index'
import type { LoginRequest, LoginResponse, User } from '../types/user'

/**
 * 用户登录
 */
export function login(data: LoginRequest): Promise<LoginResponse> {
  return request({
    url: '/api/v1/auth/login',
    method: 'post',
    data,
  })
}

/**
 * 获取当前用户信息
 */
export function getCurrentUser(): Promise<User> {
  return request({
    url: '/api/v1/auth/me',
    method: 'get',
  })
}

/**
 * 使用 Refresh Token 刷新 Access Token
 */
export function refreshToken(refresh_token: string): Promise<{ access_token: string; refresh_token: string; token_type: string }> {
  return request({
    url: '/api/v1/auth/refresh',
    method: 'post',
    data: { refresh_token },
  })
}

/**
 * 用户自助修改密码
 */
export function changePassword(old_password: string, new_password: string): Promise<{ detail: string }> {
  return request({
    url: '/api/v1/auth/password',
    method: 'put',
    data: { old_password, new_password },
  })
}
