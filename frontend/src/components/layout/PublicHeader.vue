<template>
  <header
    class="public-header"
    :class="{
      'header-home': isHome && !isScrolled,
      'header-scrolled': isScrolled || !isHome,
    }"
  >
    <div class="header-container">
      <!-- Logo -->
      <div class="header-logo" @click="router.push('/')">
        <img src="/logo.png" alt="视觉北化" class="logo-image" />
      </div>

      <!-- 搜索框 - 仅在非首页或滚动后显示 -->
      <div
        v-if="!isHome || isScrolled"
        class="header-search-mini"
      >
        <n-input
          v-model:value="localKeyword"
          :placeholder="smartSearchEnabled ? '试试自然语言搜索...' : '搜索照片、描述或标签'"
          clearable
          size="small"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
          <template #suffix>
            <n-button
              type="primary"
              size="tiny"
              class="search-btn-red"
              @click="handleSearch"
            >
              <n-icon :component="SearchOutline" />
            </n-button>
          </template>
        </n-input>
        <div class="header-smart-toggle">
          <n-switch
            v-model:value="smartSearchEnabled"
            size="small"
            @update:value="handleSmartToggle"
          />
          <n-text depth="3" class="smart-label" :class="{ 'smart-active': smartSearchEnabled }">
            {{ smartSearchEnabled ? '✨ 智能' : '普通' }}
          </n-text>
        </div>
      </div>

      <!-- 右侧操作区 -->
      <div class="header-actions">
        <n-button
          v-if="authStore.isAuthenticated"
          quaternary
          size="small"
          @click="router.push('/upload')"
        >
          <template #icon>
            <n-icon :component="CloudUploadOutline" />
          </template>
          <span class="action-text">上传</span>
        </n-button>

        <NotificationBell v-if="authStore.isAuthenticated" />

        <template v-if="authStore.isAuthenticated">
          <n-dropdown :options="userMenuOptions" @select="handleUserMenuSelect">
            <n-button circle size="small">
              <template #icon>
                <n-icon :component="PersonOutline" />
              </template>
            </n-button>
          </n-dropdown>
        </template>
        <template v-else>
          <n-button
            type="primary"
            size="small"
            class="login-btn"
            @click="router.push('/login')"
          >
            登录
          </n-button>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, useDialog, useMessage } from 'naive-ui'
import {
  CloudUploadOutline,
  LogOutOutline,
  PersonOutline,
  SearchOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import { useWindowScroll } from '@vueuse/core'
import NotificationBell from '../common/NotificationBell.vue'
import { useAuthStore } from '../../stores/auth'

interface Props {
  isHome?: boolean
  searchKeyword?: string
}

const props = withDefaults(defineProps<Props>(), {
  isHome: false,
  searchKeyword: '',
})

const emit = defineEmits<{
  search: [keyword: string, smart: boolean]
  openChangePassword: []
}>()

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()
const { y: scrollY } = useWindowScroll()

const isScrolled = computed(() => scrollY.value > 60)
const localKeyword = ref(props.searchKeyword)
const smartSearchEnabled = ref(true)

onMounted(() => {
  const saved = localStorage.getItem('smart_search_enabled')
  smartSearchEnabled.value = saved !== 'false'
})

function handleSmartToggle(enabled: boolean) {
  smartSearchEnabled.value = enabled
  localStorage.setItem('smart_search_enabled', enabled ? 'true' : 'false')
}

const userMenuOptions = computed(() => {
  const options: any[] = [
    { label: authStore.user?.email || '用户', key: 'user-info', disabled: true },
    { label: '我的投稿', key: 'submissions' },
  ]
  if (authStore.isAuditor) {
    options.push({
      label: '管理后台',
      key: 'admin',
      icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }),
    })
  }
  options.push(
    { label: '个人中心', key: 'profile' },
    { label: '修改密码', key: 'change-password' },
    {
      label: '退出登录',
      key: 'logout',
      icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }),
    },
  )
  return options
})

function handleSearch() {
  emit('search', localKeyword.value, smartSearchEnabled.value)
}

function handleUserMenuSelect(key: string) {
  if (key === 'admin') router.push('/admin')
  else if (key === 'submissions') router.push('/my-submissions')
  else if (key === 'profile') router.push('/profile')
  else if (key === 'change-password') {
    emit('openChangePassword')
  }
  else if (key === 'logout') {
    dialog.warning({
      title: '确认退出',
      content: '确定要退出登录吗？',
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => {
        authStore.logout()
        message.success('已退出登录')
        router.push('/login')
      },
    })
  }
}
</script>

<style scoped>
.public-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 56px;
  transition: all 0.3s ease;
}

.header-home {
  background: transparent;
}

.header-scrolled {
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-container {
  max-width: 1440px;
  margin: 0 auto;
  height: 100%;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  flex-shrink: 0;
  user-select: none;
}

.logo-image {
  height: 36px;
  width: auto;
  display: block;
}

.header-search-mini {
  flex: 1;
  max-width: 480px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-smart-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.smart-label {
  font-size: 11px;
  transition: color 0.3s ease;
  white-space: nowrap;
}

.smart-label.smart-active {
  color: #e60012;
  font-weight: 500;
}

.header-search-mini :deep(.n-input) {
  background: #f5f5f5;
  border-radius: 20px;
}

.header-search-mini :deep(.n-input__border) {
  border: none;
}

.header-search-mini :deep(.n-input__state-border) {
  border: none;
}

.header-search-mini :deep(.n-input__suffix) {
  padding-right: 4px;
}

.search-btn-red {
  background: #e60012 !important;
  border-radius: 50% !important;
  width: 28px;
  height: 28px;
  padding: 0 !important;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.login-btn {
  background: #e60012 !important;
  border-color: #e60012 !important;
}

.login-btn:hover {
  background: #c4000f !important;
  border-color: #c4000f !important;
}

@media (max-width: 768px) {
  .header-container {
    padding: 0 12px;
  }

  .logo-image {
    height: 28px;
  }

  .action-text {
    display: none;
  }

  .header-search-mini {
    max-width: 200px;
  }
}

@media (max-width: 480px) {
  .header-search-mini {
    display: none;
  }
}
</style>
