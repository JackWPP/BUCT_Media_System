/**
 * 应用全局状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 状态
  const darkMode = ref(false)
  const sidebarCollapsed = ref(false)
  const loading = ref(false)

  // 切换暗色模式
  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    // 可以在这里添加持久化逻辑
    localStorage.setItem('dark_mode', darkMode.value ? '1' : '0')
  }

  // 切换侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // 设置全局加载状态
  function setLoading(value: boolean) {
    loading.value = value
  }

  // 初始化
  function init() {
    const storedDarkMode = localStorage.getItem('dark_mode')
    if (storedDarkMode) {
      darkMode.value = storedDarkMode === '1'
    }
  }

  return {
    darkMode,
    sidebarCollapsed,
    loading,
    toggleDarkMode,
    toggleSidebar,
    setLoading,
    init,
  }
})
