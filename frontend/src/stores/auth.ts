/**
 * 认证状态管理
 * 
 * 包含用户登录状态、角色权限判断等功能。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserRole } from '../types/user'
import * as authApi from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value)

  /**
   * 是否为超级管理员
   */
  const isAdmin = computed(() => user.value?.role === 'admin')

  /**
   * 是否为审核员（包含管理员）
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

  // 从 localStorage 初始化
  function initFromStorage() {
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      token.value = storedToken
      // 尝试获取用户信息
      fetchCurrentUser().catch(() => {
        // 如果获取失败，清除 token
        logout()
      })
    }
  }

  // 用户登录（支持学号或邮箱）
  async function login(identifier: string, password: string) {
    try {
      const response = await authApi.login({ identifier, password })
      token.value = response.access_token
      user.value = response.user

      // 保存 token 到 localStorage
      localStorage.setItem('auth_token', response.access_token)

      return response
    } catch (error) {
      throw error
    }
  }

  // 用户登出
  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
  }

  // 获取当前用户信息
  async function fetchCurrentUser() {
    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData
      return userData
    } catch (error) {
      throw error
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    isAdmin,
    isAuditor,
    canReview,
    hasRole,
    initFromStorage,
    login,
    logout,
    fetchCurrentUser,
  }
})

