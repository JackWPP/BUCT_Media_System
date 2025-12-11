/**
 * 认证状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '../types/user'
import * as authApi from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value)

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

  // 用户登录
  async function login(email: string, password: string) {
    try {
      const response = await authApi.login({ email, password })
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
    initFromStorage,
    login,
    logout,
    fetchCurrentUser,
  }
})
