/**
 * 格式化工具函数
 */
import dayjs from 'dayjs'

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number | null): string {
  if (!bytes) return '未知'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

/**
 * 格式化日期时间
 */
export function formatDate(date: string | Date | null, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) return '未知'
  return dayjs(date).format(format)
}

/**
 * 格式化相对时间
 */
export function formatRelativeTime(date: string | Date | null): string {
  if (!date) return '未知'
  const now = dayjs()
  const target = dayjs(date)
  const diff = now.diff(target, 'second')

  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`

  return target.format('YYYY-MM-DD')
}

/**
 * 截断文本
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

/**
 * 获取图片 URL
 */
export function getImageUrl(path: string | null, baseUrl?: string): string {
  if (!path) return ''
  const base = baseUrl || import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '/api')
  return `${base}${path.startsWith('/') ? '' : '/'}${path}`
}

export function getPhotoUrl(photoId: string, type: 'original' | 'thumbnail' = 'original'): string {
  // In production, use empty base (relative path) since Nginx handles /api proxy
  // In development, use full localhost URL
  const base = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '')
  return `${base}/api/v1/photos/${photoId}/image/${type}`
}
