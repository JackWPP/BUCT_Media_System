/**
 * 请求相关工具函数
 */

/**
 * 构建查询字符串
 */
export function buildQueryString(params: Record<string, any>): string {
  const query = new URLSearchParams()
  
  Object.keys(params).forEach((key) => {
    const value = params[key]
    if (value !== null && value !== undefined && value !== '') {
      query.append(key, String(value))
    }
  })
  
  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

/**
 * 下载文件
 */
export function downloadFile(url: string, filename: string): void {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/**
 * 复制到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    console.error('Copy failed:', error)
    return false
  }
}
