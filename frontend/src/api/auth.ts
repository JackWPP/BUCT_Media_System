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
    url: '/api/v1/login',
    method: 'post',
    data,
  })
}

/**
 * 获取当前用户信息
 */
export function getCurrentUser(): Promise<User> {
  return request({
    url: '/api/v1/me',
    method: 'get',
  })
}
