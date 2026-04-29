/**
 * Axios 请求封装
 *
 * 包含 Token 自动刷新、全局错误处理等功能。
 *
 * 注意：响应拦截器返回 response.data（已解包），
 * 因此 request.get<T>() 实际返回 Promise<T>，而非 Promise<AxiosResponse<T>>。
 */
import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import type { ApiError } from '../types/api'

type RequestFn = {
  <T = any>(config: any): Promise<T>
  get<T = any>(url: string, config?: any): Promise<T>
  post<T = any>(url: string, data?: any, config?: any): Promise<T>
  put<T = any>(url: string, data?: any, config?: any): Promise<T>
  patch<T = any>(url: string, data?: any, config?: any): Promise<T>
  delete<T = any>(url: string, config?: any): Promise<T>
}

// 全局错误处理器(在App.vue中设置)
let globalErrorHandler: ((message: string, type: 'error' | 'warning' | 'info') => void) | null = null

export function setGlobalErrorHandler(handler: (message: string, type: 'error' | 'warning' | 'info') => void) {
  globalErrorHandler = handler
}

// 创建 axios 实例
const _axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

const request = _axiosInstance as unknown as RequestFn

// ────────────────────────────────────────────────────────────
// Token 刷新状态管理
// ────────────────────────────────────────────────────────────
let isRefreshing = false
let failedQueue: { resolve: (value: any) => void; reject: (error: any) => void }[] = []

function processQueue(error: any, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// 请求拦截器
_axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
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
_axiosInstance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const { response } = error

    if (
      response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/login')
    ) {
      const refreshTokenStr = localStorage.getItem('refresh_token')

      if (refreshTokenStr) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject })
          }).then((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return _axiosInstance(originalRequest)
          })
        }

        originalRequest._retry = true
        isRefreshing = true

        try {
          const baseURL = import.meta.env.VITE_API_BASE_URL || ''
          const res = await axios.post(`${baseURL}/api/v1/auth/refresh`, {
            refresh_token: refreshTokenStr,
          })

          const { access_token, refresh_token } = res.data
          localStorage.setItem('auth_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          processQueue(null, access_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return _axiosInstance(originalRequest)
        } catch (refreshError) {
          processQueue(refreshError, null)
          localStorage.removeItem('auth_token')
          localStorage.removeItem('refresh_token')
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      }
    }

    let errorMessage = '请求失败'

    if (response) {
      switch (response.status) {
        case 400:
          errorMessage = response.data?.detail || '请求参数错误'
          break
        case 401:
          errorMessage = '身份验证失败，请重新登录'
          localStorage.removeItem('auth_token')
          localStorage.removeItem('refresh_token')
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
        case 429:
          errorMessage = '操作过于频繁，请稍后再试'
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

    if (globalErrorHandler) {
      globalErrorHandler(errorMessage, 'error')
    }

    console.error('API Error:', errorMessage, error)
    return Promise.reject(error)
  }
)

export default request
