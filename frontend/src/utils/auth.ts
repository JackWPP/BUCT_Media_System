/**
 * 认证相关工具函数
 */

const TOKEN_KEY = 'auth_token'

/**
 * 获取存储的 token
 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 设置 token
 */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 移除 token
 */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
  return !!getToken()
}
