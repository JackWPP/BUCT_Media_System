/**
 * Axios 请求封装
 */
import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import type { ApiError } from '../types/api'

// 全局错误处理器(在App.vue中设置)
let globalErrorHandler: ((message: string, type: 'error' | 'warning' | 'info') => void) | null = null

export function setGlobalErrorHandler(handler: (message: string, type: 'error' | 'warning' | 'info') => void) {
  globalErrorHandler = handler
}

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error: AxiosError<ApiError>) => {
    const { response } = error
    let errorMessage = '请求失败'

    // 处理不同的错误状态码
    if (response) {
      switch (response.status) {
        case 400:
          errorMessage = response.data?.detail || '请求参数错误'
          break
        case 401:
          errorMessage = '身份验证失败，请重新登录'
          // 未授权，清除 token 并跳转到登录页
          localStorage.removeItem('auth_token')
          if (window.location.pathname !== '/login') {
            setTimeout(() => {
              window.location.href = '/login'
            }, 1000)
          }
          break
        case 403:
          errorMessage = '权限不足，无法访问该资源'
          break
        case 404:
          errorMessage = '请求的资源不存在'
          break
        case 422:
          errorMessage = response.data?.detail || '数据验证失败'
          break
        case 500:
          errorMessage = '服务器错误，请稍后重试'
          break
        case 502:
        case 503:
          errorMessage = '服务暂时不可用，请稍后重试'
          break
        default:
          errorMessage = response.data?.detail || `请求失败 (${response.status})`
      }
    } else if (error.request) {
      errorMessage = '网络错误，请检查网络连接'
    } else {
      errorMessage = '请求配置错误'
    }

    // 调用全局错误处理器
    if (globalErrorHandler) {
      globalErrorHandler(errorMessage, 'error')
    }

    console.error('API Error:', errorMessage, error)
    return Promise.reject(error)
  }
)

export default request
