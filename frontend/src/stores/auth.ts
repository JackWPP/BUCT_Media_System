/**
 * 认证状态管理
 *
 * 包含用户登录状态、角色权限判断、Token 自动刷新等功能。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserRole } from '../types/user'
import * as authApi from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const refreshTokenValue = ref<string | null>(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value)

  /**
   * 是否为超级管理员
   */
  const isAdmin = computed(() => user.value?.role === 'admin')

  /**
   * 是否为审核员（包含管理员）
   * 用于内容审核相关能力，不代表拥有系统管理权限。
   */
  const isAuditor = computed(() =>
    user.value?.role === 'admin' || user.value?.role === 'auditor'
  )

  /**
   * 是否有审核权限（管理员或审核员）
   */
  const canReview = computed(() => isAuditor.value)

  /**
   * 检查用户是否拥有指定角色
   */
  function hasRole(role: UserRole | UserRole[]): boolean {
    if (!user.value) return false
    if (Array.isArray(role)) {
      return role.includes(user.value.role)
    }
    return user.value.role === role
  }

  // 从 localStorage / sessionStorage 初始化
  function initFromStorage() {
    let storedToken = localStorage.getItem('auth_token')
    let storedRefreshToken = localStorage.getItem('refresh_token')
    // 兼容未勾选"记住我"时存储在 sessionStorage 的情况
    if (!storedToken) {
      storedToken = sessionStorage.getItem('auth_token')
      storedRefreshToken = sessionStorage.getItem('refresh_token')
    }
    if (storedToken) {
      token.value = storedToken
      refreshTokenValue.value = storedRefreshToken
      // 尝试获取用户信息
      fetchCurrentUser().catch(() => {
        // Access Token 可能过期，尝试刷新
        if (storedRefreshToken) {
          refreshAccessToken().catch(() => {
            logout()
          })
        } else {
          logout()
        }
      })
    }
  }

  // 用户登录（支持学号或邮箱）
  async function login(identifier: string, password: string) {
    const response = await authApi.login({ identifier, password })
    token.value = response.access_token
    refreshTokenValue.value = response.refresh_token
    user.value = response.user

    // 保存 token 到 localStorage
    localStorage.setItem('auth_token', response.access_token)
    localStorage.setItem('refresh_token', response.refresh_token)

    return response
  }

  // 用户登出
  function logout() {
    user.value = null
    token.value = null
    refreshTokenValue.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    sessionStorage.removeItem('auth_token')
    sessionStorage.removeItem('refresh_token')
  }

  // 获取当前用户信息
  async function fetchCurrentUser() {
    const userData = await authApi.getCurrentUser()
    user.value = userData
    return userData
  }

  /**
   * 使用 Refresh Token 刷新 Access Token
   *
   * 刷新成功后更新 localStorage 和内存中的 Token。
   */
  async function refreshAccessToken() {
    if (!refreshTokenValue.value) {
      throw new Error('No refresh token available')
    }

    const response = await authApi.refreshToken(refreshTokenValue.value)
    token.value = response.access_token
    refreshTokenValue.value = response.refresh_token

    localStorage.setItem('auth_token', response.access_token)
    localStorage.setItem('refresh_token', response.refresh_token)

    // 刷新后重新获取用户信息
    await fetchCurrentUser()

    return response
  }

  return {
    user,
    token,
    refreshTokenValue,
    isAuthenticated,
    isAdmin,
    isAuditor,
    canReview,
    hasRole,
    initFromStorage,
    login,
    logout,
    fetchCurrentUser,
    refreshAccessToken,
  }
})
